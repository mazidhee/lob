import sys
import os
import time
import random
import numpy as np
from dataclasses import dataclass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from lob.order import Side, OrderType, OrderStatus
from lob.matching_engine import MatchingEngine


@dataclass
class SimConfig:
    initial_mid: float = 100.0
    tick: float = 0.01
    cancel_rate: float = 0.4
    market_frac: float = 0.05
    ioc_frac: float = 0.02
    fok_frac: float = 0.01
    max_offset_ticks: int = 50
    concentration: float = 2.0
    volatility: float = 0.0005
    mean_reversion: float = 0.01
    min_qty: int = 1
    max_qty: int = 100
    seed: int | None = 42
    num_orders: int = 10000


class OrderFlowGenerator:
    """Synthetic order flow with Poisson-like arrivals and mean-reverting mid."""

    def __init__(self, config: SimConfig | None = None):
        self.cfg = config or SimConfig()
        self.rng = np.random.default_rng(self.cfg.seed)
        self.mid = self.cfg.initial_mid

    def run(self, engine: MatchingEngine) -> dict:
        self.mid = self.cfg.initial_mid
        resting: list[int] = []
        n_new = n_cancel = n_trades = 0

        for _ in range(self.cfg.num_orders):
            if resting and self.rng.random() < self.cfg.cancel_rate:
                idx = self.rng.integers(0, len(resting))
                if engine.cancel(resting.pop(idx)):
                    n_cancel += 1
                continue

            self._step_mid()
            side = Side.BUY if self.rng.random() < 0.5 else Side.SELL
            otype = self._pick_type()
            qty = self._pick_qty()
            price = self._pick_price(side) if otype != OrderType.MARKET else None

            order, trades = engine.submit(side, otype, price, qty)
            n_new += 1
            n_trades += len(trades)

            if order.order_type == OrderType.LIMIT and order.status in (
                OrderStatus.NEW, OrderStatus.PARTIALLY_FILLED
            ):
                resting.append(order.order_id)

        return {
            'submitted': n_new,
            'cancelled': n_cancel,
            'trades': n_trades,
            'resting_bids': engine.bid_count,
            'resting_asks': engine.ask_count,
        }

    def _step_mid(self):
        drift = self.cfg.mean_reversion * (self.cfg.initial_mid - self.mid)
        shock = self.rng.normal(0, self.cfg.volatility * self.mid)
        self.mid = max(self.cfg.tick, self.mid + drift + shock)
        self.mid = round(self.mid / self.cfg.tick) * self.cfg.tick

    def _pick_price(self, side: Side) -> float:
        u = self.rng.random()
        offset = max(1, int(self.cfg.max_offset_ticks * (u ** self.cfg.concentration)))
        delta = offset * self.cfg.tick
        price = self.mid - delta if side == Side.BUY else self.mid + delta
        return round(price / self.cfg.tick) * self.cfg.tick

    def _pick_qty(self) -> int:
        u = self.rng.random()
        val = self.cfg.min_qty + (self.cfg.max_qty - self.cfg.min_qty) * (1 - u ** (1 / 2.0))
        return max(self.cfg.min_qty, min(self.cfg.max_qty, int(val)))

    def _pick_type(self) -> OrderType:
        r = self.rng.random()
        if r < self.cfg.market_frac:
            return OrderType.MARKET
        r -= self.cfg.market_frac
        if r < self.cfg.ioc_frac:
            return OrderType.IOC
        r -= self.cfg.ioc_frac
        if r < self.cfg.fok_frac:
            return OrderType.FOK
        return OrderType.LIMIT
