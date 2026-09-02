import sys
import os
import time
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from lob.order import Side, OrderType, OrderStatus
from lob.matching_engine import MatchingEngine


class BenchmarkResult:
    __slots__ = ('name', 'latencies_ns', '_sorted', '_total_ns')

    def __init__(self, name: str):
        self.name = name
        self.latencies_ns: list[int] = []
        self._sorted = False
        self._total_ns = 0

    def record(self, ns: int):
        self.latencies_ns.append(ns)
        self._total_ns += ns
        self._sorted = False

    def _sort(self):
        if not self._sorted:
            self.latencies_ns.sort()
            self._sorted = True

    @property
    def count(self) -> int:
        return len(self.latencies_ns)

    def _pct(self, p: float) -> float:
        self._sort()
        idx = min(int(p * self.count), self.count - 1)
        return self.latencies_ns[idx] / 1_000.0

    @property
    def p50(self) -> float:
        return self._pct(0.50)

    @property
    def p99(self) -> float:
        return self._pct(0.99)

    @property
    def p999(self) -> float:
        return self._pct(0.999)

    @property
    def mean(self) -> float:
        return (self._total_ns / self.count / 1_000.0) if self.count else 0

    @property
    def throughput(self) -> float:
        return self.count / (self._total_ns / 1e9) if self._total_ns else 0


def _populated_engine(n_levels=100, per_level=5) -> MatchingEngine:
    engine = MatchingEngine()
    mid = 100.0
    for i in range(n_levels):
        bp = mid - (i + 1) * 0.01
        ap = mid + (i + 1) * 0.01
        for _ in range(per_level):
            q = random.randint(10, 100)
            engine.submit(Side.BUY, OrderType.LIMIT, bp, q)
            engine.submit(Side.SELL, OrderType.LIMIT, ap, q)
    return engine


def bench_insert(n=20000) -> BenchmarkResult:
    res = BenchmarkResult("Insert Limit")
    engine = _populated_engine()
    for i in range(n):
        side = Side.BUY if i % 2 == 0 else Side.SELL
        price = 90.0 + random.random() * 2.0 if side == Side.BUY else 108.0 + random.random() * 2.0
        t0 = time.perf_counter_ns()
        engine.submit(side, OrderType.LIMIT, price, random.randint(1, 50))
        res.record(time.perf_counter_ns() - t0)
    return res


def bench_cancel(n=20000) -> BenchmarkResult:
    res = BenchmarkResult("Cancel")
    engine = _populated_engine(200, 10)
    targets = []
    for _ in range(n):
        o, _ = engine.submit(Side.BUY, OrderType.LIMIT, 90.0 + random.random(), 10)
        targets.append(o.order_id)
    for oid in targets:
        t0 = time.perf_counter_ns()
        engine.cancel(oid)
        res.record(time.perf_counter_ns() - t0)
    return res


def bench_mixed(n=20000) -> BenchmarkResult:
    res = BenchmarkResult("Mixed")
    engine = _populated_engine()
    resting = list(engine._orders.keys())
    for i in range(n):
        r = random.random()
        t0 = time.perf_counter_ns()
        if r < 0.70:
            side = Side.BUY if random.random() < 0.5 else Side.SELL
            p = 99.0 + random.random() if side == Side.BUY else 101.0 + random.random()
            o, _ = engine.submit(side, OrderType.LIMIT, p, random.randint(1, 50))
            if o.status in (OrderStatus.NEW, OrderStatus.PARTIALLY_FILLED):
                resting.append(o.order_id)
        elif r < 0.85 and resting:
            engine.cancel(resting.pop(random.randint(0, len(resting) - 1)))
        else:
            side = Side.BUY if random.random() < 0.5 else Side.SELL
            engine.submit(side, OrderType.MARKET, quantity=random.randint(1, 20))
        res.record(time.perf_counter_ns() - t0)
    return res


def run_benchmarks(n=20000):
    results = [bench_insert(n), bench_cancel(n), bench_mixed(n)]

    header = f"{'Operation':<16} {'Ops':>8} {'Throughput':>14} {'Mean':>9} {'p50':>9} {'p99':>9} {'p99.9':>9}"
    sep = "-" * len(header)
    lines = [sep, header, sep]
    for r in results:
        lines.append(
            f"{r.name:<16} {r.count:>8,} {r.throughput:>12,.0f}/s "
            f"{r.mean:>7.1f}us {r.p50:>7.1f}us {r.p99:>7.1f}us {r.p999:>7.1f}us"
        )
    lines.append(sep)
    return "\n".join(lines)


if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    report = run_benchmarks(n)
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stdout.write(report + "\n")
