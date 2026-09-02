from sortedcontainers import SortedDict

from lob.order import Order, Side
from lob.price_level import PriceLevel, Node


class OrderBookSide:
    """One side (bids or asks) of the book.

    SortedDict[sort_key] -> PriceLevel gives O(log P) insertion of new price
    levels where P = number of distinct active prices (not orders).

    For bids we negate the key so peekitem(0) always returns best price.
    A separate dict maps order_id -> (Node, price) for O(1) cancel.
    """
    __slots__ = ('_side', '_levels', '_index', '_is_bid')

    def __init__(self, side: Side):
        self._side = side
        self._is_bid = side == Side.BUY
        self._levels: SortedDict = SortedDict()
        self._index: dict[int, tuple[Node, float]] = {}

    def _key(self, price: float) -> float:
        return -price if self._is_bid else price

    def add(self, order: Order) -> None:
        key = self._key(order.price)
        if key not in self._levels:
            self._levels[key] = PriceLevel(order.price)
        node = self._levels[key].append(order)
        self._index[order.order_id] = (node, order.price)

    def remove(self, order_id: int) -> Order:
        node, price = self._index.pop(order_id)
        key = self._key(price)
        level = self._levels[key]
        level.remove(node)
        if level.is_empty():
            del self._levels[key]
        return node.order

    def best_price(self) -> float | None:
        if not self._levels:
            return None
        key = self._levels.peekitem(0)[0]
        return -key if self._is_bid else key

    def best_level(self) -> PriceLevel | None:
        if not self._levels:
            return None
        return self._levels.peekitem(0)[1]

    def remove_level(self, price: float) -> None:
        key = self._key(price)
        if key in self._levels:
            for order in self._levels[key]:
                self._index.pop(order.order_id, None)
            del self._levels[key]

    def has(self, order_id: int) -> bool:
        return order_id in self._index

    def get_node(self, order_id: int) -> Node | None:
        entry = self._index.get(order_id)
        return entry[0] if entry else None

    def depth(self, n: int = 10) -> list[tuple[float, int, int]]:
        """Top N levels as [(price, total_qty, order_count), ...]."""
        result = []
        for i, key in enumerate(self._levels):
            if i >= n:
                break
            lvl = self._levels[key]
            result.append((lvl.price, lvl.total_qty, lvl.order_count))
        return result

    def volume(self) -> int:
        return sum(lvl.total_qty for lvl in self._levels.values())

    @property
    def num_orders(self) -> int:
        return len(self._index)

    @property
    def num_levels(self) -> int:
        return len(self._levels)

    def is_empty(self) -> bool:
        return not self._levels

    def __len__(self) -> int:
        return len(self._index)

    def __repr__(self) -> str:
        side = "BIDS" if self._is_bid else "ASKS"
        return f"OrderBookSide({side}, levels={self.num_levels}, orders={self.num_orders})"
