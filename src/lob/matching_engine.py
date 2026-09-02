from lob.order import Order, Trade, Side, OrderType, OrderStatus, IdGenerator, timestamp_ns
from lob.order_book import OrderBookSide


class MatchingEngine:
    """Single-instrument matching engine implementing strict price-time priority.

    Deterministic: same input sequence always produces the same output.
    Single-threaded by design — real exchanges run one matching thread per
    instrument to guarantee ordering. Concurrency belongs at the gateway layer.
    """
    __slots__ = ('_bids', '_asks', '_next_order_id', '_next_trade_id',
                 '_orders', '_trades')

    def __init__(self):
        self._bids = OrderBookSide(Side.BUY)
        self._asks = OrderBookSide(Side.SELL)
        self._next_order_id = IdGenerator()
        self._next_trade_id = IdGenerator()
        self._orders: dict[int, Order] = {}
        self._trades: list[Trade] = []

    def submit(self, side: Side, order_type: OrderType,
               price: float | None = None, quantity: int = 0) -> tuple[Order, list[Trade]]:
        """Public entry point — creates an Order and processes it."""
        if quantity <= 0:
            raise ValueError("quantity must be > 0")
        if order_type != OrderType.MARKET and price is None:
            raise ValueError("price required for non-MARKET orders")

        order = Order(
            order_id=self._next_order_id(),
            side=side,
            order_type=order_type,
            price=price,
            quantity=quantity,
            remaining_qty=quantity,
            timestamp=timestamp_ns(),
        )
        self._orders[order.order_id] = order
        trades = self._process(order)
        return order, trades

    def _process(self, order: Order) -> list[Trade]:
        if order.order_type == OrderType.FOK:
            if not self._can_fill(order):
                order.status = OrderStatus.CANCELLED
                return []

        trades = self._match(order)

        if order.remaining_qty > 0:
            if order.order_type == OrderType.LIMIT:
                book = self._bids if order.side == Side.BUY else self._asks
                book.add(order)
            else:
                order.status = OrderStatus.CANCELLED

        return trades

    def _match(self, order: Order) -> list[Trade]:
        """Core matching loop — walks the opposite book at price-time priority."""
        trades = []
        opposite = self._asks if order.side == Side.BUY else self._bids

        while order.remaining_qty > 0 and not opposite.is_empty():
            level = opposite.best_level()
            if not self._crosses(order, level.price):
                break

            while order.remaining_qty > 0 and not level.is_empty():
                resting = level.front()
                fill_qty = min(order.remaining_qty, resting.remaining_qty)

                trade = Trade(
                    trade_id=self._next_trade_id(),
                    resting_order_id=resting.order_id,
                    aggressor_order_id=order.order_id,
                    price=level.price,
                    quantity=fill_qty,
                    timestamp=timestamp_ns(),
                    resting_side=resting.side,
                    aggressor_side=order.side,
                )
                trades.append(trade)
                self._trades.append(trade)

                order.remaining_qty -= fill_qty
                resting.remaining_qty -= fill_qty
                level._total_qty -= fill_qty

                if resting.remaining_qty == 0:
                    resting.status = OrderStatus.FILLED
                    opposite.remove(resting.order_id)
                else:
                    resting.status = OrderStatus.PARTIALLY_FILLED

            if level.is_empty():
                opposite.remove_level(level.price)

        if order.remaining_qty == 0:
            order.status = OrderStatus.FILLED
        elif order.remaining_qty < order.quantity:
            order.status = OrderStatus.PARTIALLY_FILLED

        return trades

    def _crosses(self, order: Order, resting_price: float) -> bool:
        if order.order_type == OrderType.MARKET or order.price is None:
            return True
        if order.side == Side.BUY:
            return order.price >= resting_price
        return order.price <= resting_price

    def _can_fill(self, order: Order) -> bool:
        """Walk opposite side to check if FOK can fill completely."""
        opposite = self._asks if order.side == Side.BUY else self._bids
        needed = order.quantity
        for key in opposite._levels:
            level = opposite._levels[key]
            if not self._crosses(order, level.price):
                break
            needed -= level.total_qty
            if needed <= 0:
                return True
        return False

    def cancel(self, order_id: int) -> bool:
        order = self._orders.get(order_id)
        if not order or order.status in (OrderStatus.FILLED, OrderStatus.CANCELLED):
            return False
        book = self._bids if order.side == Side.BUY else self._asks
        if not book.has(order_id):
            return False
        book.remove(order_id)
        order.status = OrderStatus.CANCELLED
        return True

    def modify(self, order_id: int, new_price: float | None = None,
               new_qty: int | None = None) -> list[Trade]:
        """Modify a resting order.

        Price change or qty increase: cancel + re-insert (loses time priority).
        Qty decrease only: in-place mutation (keeps time priority).
        """
        order = self._orders.get(order_id)
        if not order or order.status in (OrderStatus.FILLED, OrderStatus.CANCELLED):
            return []
        book = self._bids if order.side == Side.BUY else self._asks
        if not book.has(order_id):
            return []

        price_changed = new_price is not None
        qty_increased = new_qty is not None and new_qty > order.remaining_qty

        if price_changed or qty_increased:
            book.remove(order_id)
            if new_price is not None:
                order.price = new_price
            if new_qty is not None:
                order.quantity = new_qty + (order.quantity - order.remaining_qty)
                order.remaining_qty = new_qty
            order.timestamp = timestamp_ns()
            return self._process(order)

        if new_qty is not None and new_qty < order.remaining_qty:
            diff = order.remaining_qty - new_qty
            order.remaining_qty = new_qty
            order.quantity -= diff
            node = book.get_node(order_id)
            if node:
                level_key = book._key(order.price)
                book._levels[level_key]._total_qty -= diff

        return []

    def snapshot(self, depth: int = 10) -> dict:
        best_bid, best_ask = self.bbo()
        spread = (best_ask - best_bid) if (best_bid and best_ask) else None
        return {
            'bids': self._bids.depth(depth),
            'asks': self._asks.depth(depth),
            'best_bid': best_bid,
            'best_ask': best_ask,
            'spread': spread,
        }

    def bbo(self) -> tuple[float | None, float | None]:
        return self._bids.best_price(), self._asks.best_price()

    def get_order(self, order_id: int) -> Order | None:
        return self._orders.get(order_id)

    @property
    def trade_log(self) -> list[Trade]:
        return list(self._trades)

    @property
    def bid_count(self) -> int:
        return self._bids.num_orders

    @property
    def ask_count(self) -> int:
        return self._asks.num_orders

    @property
    def trade_count(self) -> int:
        return len(self._trades)

    def __repr__(self) -> str:
        return f"MatchingEngine(bids={self.bid_count}, asks={self.ask_count}, trades={self.trade_count})"
