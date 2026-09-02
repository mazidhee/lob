from lob.order import Order


class Node:
    """Doubly-linked list node wrapping an Order."""
    __slots__ = ('order', 'prev', 'next')

    def __init__(self, order: Order):
        self.order = order
        self.prev: Node | None = None
        self.next: Node | None = None


class PriceLevel:
    """FIFO queue at a single price. O(1) append, pop_front, and cancel-by-node.

    Backed by a doubly-linked list so we get O(1) removal of any arbitrary
    order — deque gives O(1) at the ends but O(n) for mid-queue cancels,
    and real books see cancels far more often than fills.
    """
    __slots__ = ('price', '_head', '_tail', '_size', '_total_qty')

    def __init__(self, price: float):
        self.price = price
        self._head: Node | None = None
        self._tail: Node | None = None
        self._size = 0
        self._total_qty = 0

    def append(self, order: Order) -> Node:
        node = Node(order)
        if self._tail is None:
            self._head = self._tail = node
        else:
            self._tail.next = node
            node.prev = self._tail
            self._tail = node
        self._size += 1
        self._total_qty += order.remaining_qty
        return node

    def pop_front(self) -> Node:
        if self._head is None:
            raise IndexError("pop from empty PriceLevel")
        node = self._head
        self._head = node.next
        if self._head is None:
            self._tail = None
        else:
            self._head.prev = None
        node.prev = node.next = None
        self._size -= 1
        self._total_qty -= node.order.remaining_qty
        return node

    def remove(self, node: Node) -> None:
        if node.prev:
            node.prev.next = node.next
        elif self._head is node:
            self._head = node.next

        if node.next:
            node.next.prev = node.prev
        elif self._tail is node:
            self._tail = node.prev

        node.prev = node.next = None
        self._size -= 1
        self._total_qty -= node.order.remaining_qty

    def front(self) -> Order | None:
        return self._head.order if self._head else None

    def is_empty(self) -> bool:
        return self._size == 0

    @property
    def total_qty(self) -> int:
        return self._total_qty

    @property
    def order_count(self) -> int:
        return self._size

    def __len__(self) -> int:
        return self._size

    def __iter__(self):
        cur = self._head
        while cur:
            yield cur.order
            cur = cur.next

    def __repr__(self) -> str:
        return f"PriceLevel({self.price}, orders={self._size}, qty={self._total_qty})"
