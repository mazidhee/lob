import time
from dataclasses import dataclass
from enum import Enum, auto


class Side(Enum):
    BUY = auto()
    SELL = auto()


class OrderType(Enum):
    LIMIT = auto()
    MARKET = auto()
    IOC = auto()
    FOK = auto()


class OrderStatus(Enum):
    NEW = auto()
    PARTIALLY_FILLED = auto()
    FILLED = auto()
    CANCELLED = auto()


@dataclass(slots=True)
class Order:
    order_id: int
    side: Side
    order_type: OrderType
    price: float | None
    quantity: int
    remaining_qty: int
    timestamp: int
    status: OrderStatus = OrderStatus.NEW


@dataclass(slots=True)
class Trade:
    trade_id: int
    resting_order_id: int
    aggressor_order_id: int
    price: float
    quantity: int
    timestamp: int
    resting_side: Side
    aggressor_side: Side


class IdGenerator:
    __slots__ = ('_counter',)

    def __init__(self, start: int = 1):
        self._counter = start

    def __call__(self) -> int:
        val = self._counter
        self._counter += 1
        return val


def timestamp_ns() -> int:
    return time.perf_counter_ns()
