import random
import pytest
from lob.order import Order, Side, OrderType, OrderStatus, IdGenerator, timestamp_ns
from lob.matching_engine import MatchingEngine
from lob.naive_order_book import NaiveMatchingEngine


@pytest.mark.slow
def test_high_volume():
    engine = MatchingEngine()
    rng = random.Random(42)
    resting = []

    for _ in range(10_000):
        side = Side.BUY if rng.random() < 0.5 else Side.SELL
        if resting and rng.random() < 0.3:
            engine.cancel(resting.pop(rng.randint(0, len(resting) - 1)))
            continue
        price = 100.0 + rng.uniform(-5, 5)
        o, _ = engine.submit(side, OrderType.LIMIT, round(price, 2), rng.randint(1, 100))
        if o.status in (OrderStatus.NEW, OrderStatus.PARTIALLY_FILLED):
            resting.append(o.order_id)

    bid, ask = engine.bbo()
    if bid is not None and ask is not None:
        assert bid < ask

    for order in engine._orders.values():
        assert order.remaining_qty >= 0


@pytest.mark.slow
def test_cancel_storm():
    engine = MatchingEngine()
    ids = []
    for i in range(1000):
        o, _ = engine.submit(Side.BUY, OrderType.LIMIT, 100.0 - i * 0.01, 10)
        ids.append(o.order_id)
    for oid in ids:
        engine.cancel(oid)
    assert engine.bid_count == 0
    assert engine._bids.is_empty()


@pytest.mark.slow
def test_one_sided_then_sweep():
    engine = MatchingEngine()
    for i in range(500):
        engine.submit(Side.BUY, OrderType.LIMIT, 100.0 - i * 0.01, 10)
    _, trades = engine.submit(Side.SELL, OrderType.MARKET, quantity=5000)
    assert engine.bid_count == 0
    total_filled = sum(t.quantity for t in trades)
    assert total_filled == 5000


@pytest.mark.slow
def test_cross_validation():
    """Run same sequence through optimized and naive engine, compare trades."""
    opt = MatchingEngine()
    naive = NaiveMatchingEngine()
    rng = random.Random(123)
    resting_ids = []

    opt_trades = []
    naive_trades = []

    for _ in range(3000):
        side = Side.BUY if rng.random() < 0.5 else Side.SELL
        r = rng.random()

        if r < 0.7:
            price = round(100.0 + rng.uniform(-3, 3), 2)
            qty = rng.randint(1, 50)
            o1, t1 = opt.submit(side, OrderType.LIMIT, price, qty)
            _, t2 = naive.submit(side, OrderType.LIMIT, price, qty, order_id=o1.order_id, ts=o1.timestamp)
            if o1.status in (OrderStatus.NEW, OrderStatus.PARTIALLY_FILLED):
                resting_ids.append(o1.order_id)
        elif r < 0.85:
            qty = rng.randint(1, 30)
            o1, t1 = opt.submit(side, OrderType.MARKET, quantity=qty)
            _, t2 = naive.submit(side, OrderType.MARKET, quantity=qty, order_id=o1.order_id, ts=o1.timestamp)
        else:
            if resting_ids:
                cancel_id = resting_ids.pop(rng.randint(0, len(resting_ids) - 1))
                opt.cancel(cancel_id)
                naive.cancel(cancel_id)
            continue

        for t in t1:
            opt_trades.append((t.price, t.quantity, t.resting_side, t.aggressor_side))
        for t in t2:
            naive_trades.append((t.price, t.quantity, t.resting_side, t.aggressor_side))

    assert len(opt_trades) == len(naive_trades), f"Trade count mismatch: {len(opt_trades)} vs {len(naive_trades)}"
    for i, (a, b) in enumerate(zip(opt_trades, naive_trades)):
        assert a == b, f"Trade {i} mismatch: {a} vs {b}"
