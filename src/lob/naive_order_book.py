from lob.order import Order, Trade, Side, OrderType, OrderStatus, IdGenerator, timestamp_ns


class NaiveMatchingEngine:
    """O(n) baseline matching engine used as correctness oracle.

    Same matching semantics as MatchingEngine but uses plain lists re-sorted
    on every operation. Intentionally slow, trivially correct. Used for
    cross-validation: run the same order sequence through both engines
    and assert identical trade output.
    """

    def __init__(self):
        self.bids: list[Order] = []
        self.asks: list[Order] = []
        self._next_trade_id = IdGenerator()
        self._orders: dict[int, Order] = {}
        self._trades: list[Trade] = []

    def submit(self, side: Side, order_type: OrderType,
               price: float | None = None, quantity: int = 0,
               order_id: int = 0, ts: int = 0) -> tuple[Order, list[Trade]]:
        order = Order(
            order_id=order_id,
            side=side,
            order_type=order_type,
            price=price,
            quantity=quantity,
            remaining_qty=quantity,
            timestamp=ts,
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
                if order.side == Side.BUY:
                    self.bids.append(order)
                else:
                    self.asks.append(order)
                if order.remaining_qty < order.quantity:
                    order.status = OrderStatus.PARTIALLY_FILLED
            else:
                order.status = OrderStatus.CANCELLED
        else:
            order.status = OrderStatus.FILLED

        return trades

    def _match(self, order: Order) -> list[Trade]:
        trades = []
        while order.remaining_qty > 0:
            if order.side == Side.BUY:
                self.asks.sort(key=lambda o: (o.price, o.timestamp))
                book = self.asks
            else:
                self.bids.sort(key=lambda o: (-o.price, o.timestamp))
                book = self.bids

            if not book:
                break

            resting = book[0]
            if not self._crosses(order, resting.price):
                break

            fill_qty = min(order.remaining_qty, resting.remaining_qty)
            trade = Trade(
                trade_id=self._next_trade_id(),
                resting_order_id=resting.order_id,
                aggressor_order_id=order.order_id,
                price=resting.price,
                quantity=fill_qty,
                timestamp=order.timestamp,
                resting_side=resting.side,
                aggressor_side=order.side,
            )
            trades.append(trade)
            self._trades.append(trade)

            order.remaining_qty -= fill_qty
            resting.remaining_qty -= fill_qty

            if resting.remaining_qty == 0:
                resting.status = OrderStatus.FILLED
                book.pop(0)
            else:
                resting.status = OrderStatus.PARTIALLY_FILLED

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
        if order.side == Side.BUY:
            self.asks.sort(key=lambda o: (o.price, o.timestamp))
            book = self.asks
        else:
            self.bids.sort(key=lambda o: (-o.price, o.timestamp))
            book = self.bids

        needed = order.quantity
        for resting in book:
            if not self._crosses(order, resting.price):
                break
            needed -= resting.remaining_qty
            if needed <= 0:
                return True
        return False

    def cancel(self, order_id: int) -> bool:
        for book in (self.bids, self.asks):
            for i, o in enumerate(book):
                if o.order_id == order_id:
                    o.status = OrderStatus.CANCELLED
                    book.pop(i)
                    return True
        return False

    def bbo(self) -> tuple[float | None, float | None]:
        self.bids.sort(key=lambda o: (-o.price, o.timestamp))
        self.asks.sort(key=lambda o: (o.price, o.timestamp))
        best_bid = self.bids[0].price if self.bids else None
        best_ask = self.asks[0].price if self.asks else None
        return best_bid, best_ask
