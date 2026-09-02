from dataclasses import dataclass
import numpy as np


@dataclass(slots=True)
class BookSnapshot:
    timestamp: int
    best_bid: float | None
    best_ask: float | None
    bid_depth: list[tuple[float, int, int]]
    ask_depth: list[tuple[float, int, int]]
    spread: float | None
    mid_price: float | None
    imbalance: float | None


class MetricsCollector:
    """Collects trades and snapshots, computes microstructure metrics."""
    __slots__ = ('_trades', '_snapshots', '_prices', '_quantities', '_timestamps')

    def __init__(self):
        self._trades = []
        self._snapshots: list[BookSnapshot] = []
        self._prices: list[float] = []
        self._quantities: list[int] = []
        self._timestamps: list[int] = []

    def record_trade(self, trade) -> None:
        self._trades.append(trade)
        self._prices.append(trade.price)
        self._quantities.append(trade.quantity)
        self._timestamps.append(trade.timestamp)

    def record_snapshot(self, snap: BookSnapshot) -> None:
        self._snapshots.append(snap)

    def vwap(self, last_n: int | None = None) -> float | None:
        if not self._prices:
            return None
        start = max(0, len(self._prices) - last_n) if last_n else 0
        prices = self._prices[start:]
        qtys = self._quantities[start:]
        total = sum(qtys)
        if total == 0:
            return None
        return sum(p * q for p, q in zip(prices, qtys)) / total

    def spread_series(self) -> list[tuple[int, float]]:
        return [(s.timestamp, s.spread) for s in self._snapshots if s.spread is not None]

    def imbalance_series(self) -> list[tuple[int, float]]:
        return [(s.timestamp, s.imbalance) for s in self._snapshots if s.imbalance is not None]

    def mid_price_series(self) -> list[tuple[int, float]]:
        return [(s.timestamp, s.mid_price) for s in self._snapshots if s.mid_price is not None]

    def trade_price_series(self) -> list[tuple[int, float]]:
        return list(zip(self._timestamps, self._prices))

    @property
    def total_volume(self) -> int:
        return sum(self._quantities)

    @property
    def num_trades(self) -> int:
        return len(self._trades)


def book_imbalance(bid_depth: list[tuple[float, int, int]],
                   ask_depth: list[tuple[float, int, int]],
                   levels: int = 5) -> float | None:
    """(bid_vol - ask_vol) / (bid_vol + ask_vol) at top N levels. Range [-1, 1]."""
    bid_vol = sum(qty for _, qty, _ in bid_depth[:levels])
    ask_vol = sum(qty for _, qty, _ in ask_depth[:levels])
    total = bid_vol + ask_vol
    return (bid_vol - ask_vol) / total if total > 0 else None
