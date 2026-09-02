import pytest
from lob.order import Side, OrderType, OrderStatus
from lob.matching_engine import MatchingEngine


@pytest.fixture
def engine():
    return MatchingEngine()


def test_basic_match(engine):
    engine.submit(Side.SELL, OrderType.LIMIT, 100.0, 100)
    order, trades = engine.submit(Side.BUY, OrderType.LIMIT, 100.0, 40)
    assert len(trades) == 1
    assert trades[0].price == 100.0
    assert trades[0].quantity == 40
    assert order.status == OrderStatus.FILLED


def test_trade_price_is_resting(engine):
    engine.submit(Side.SELL, OrderType.LIMIT, 99.0, 50)
    _, trades = engine.submit(Side.BUY, OrderType.LIMIT, 101.0, 50)
    assert trades[0].price == 99.0


def test_partial_fill(engine):
    engine.submit(Side.SELL, OrderType.LIMIT, 100.0, 30)
    order, trades = engine.submit(Side.BUY, OrderType.LIMIT, 100.0, 50)
    assert trades[0].quantity == 30
    assert order.remaining_qty == 20
    assert order.status == OrderStatus.PARTIALLY_FILLED
    assert engine.bid_count == 1


def test_full_fill_removes(engine):
    engine.submit(Side.SELL, OrderType.LIMIT, 100.0, 50)
    engine.submit(Side.BUY, OrderType.LIMIT, 100.0, 50)
    assert engine.bid_count == 0
    assert engine.ask_count == 0


def test_no_cross_rests(engine):
    engine.submit(Side.SELL, OrderType.LIMIT, 105.0, 50)
    engine.submit(Side.BUY, OrderType.LIMIT, 100.0, 50)
    assert engine.bid_count == 1
    assert engine.ask_count == 1


def test_market_order(engine):
    engine.submit(Side.SELL, OrderType.LIMIT, 100.0, 50)
    order, trades = engine.submit(Side.BUY, OrderType.MARKET, quantity=100)
    assert len(trades) == 1
    assert trades[0].quantity == 50
    assert order.status == OrderStatus.CANCELLED
    assert order.remaining_qty == 50


def test_market_no_liquidity(engine):
    order, trades = engine.submit(Side.BUY, OrderType.MARKET, quantity=100)
    assert len(trades) == 0
    assert order.status == OrderStatus.CANCELLED


def test_ioc_partial(engine):
    engine.submit(Side.SELL, OrderType.LIMIT, 100.0, 50)
    order, trades = engine.submit(Side.BUY, OrderType.IOC, 100.0, 100)
    assert trades[0].quantity == 50
    assert order.status == OrderStatus.CANCELLED
    assert engine.bid_count == 0


def test_ioc_full(engine):
    engine.submit(Side.SELL, OrderType.LIMIT, 100.0, 100)
    order, _ = engine.submit(Side.BUY, OrderType.IOC, 100.0, 50)
    assert order.status == OrderStatus.FILLED


def test_fok_reject(engine):
    engine.submit(Side.SELL, OrderType.LIMIT, 100.0, 50)
    order, trades = engine.submit(Side.BUY, OrderType.FOK, 100.0, 100)
    assert len(trades) == 0
    assert order.status == OrderStatus.CANCELLED
    assert engine.ask_count == 1


def test_fok_fill(engine):
    engine.submit(Side.SELL, OrderType.LIMIT, 100.0, 50)
    engine.submit(Side.SELL, OrderType.LIMIT, 101.0, 50)
    order, trades = engine.submit(Side.BUY, OrderType.FOK, 101.0, 100)
    assert len(trades) == 2
    assert order.status == OrderStatus.FILLED


def test_price_priority(engine):
    engine.submit(Side.SELL, OrderType.LIMIT, 101.0, 50)
    o2, _ = engine.submit(Side.SELL, OrderType.LIMIT, 100.0, 50)
    _, trades = engine.submit(Side.BUY, OrderType.MARKET, quantity=30)
    assert trades[0].resting_order_id == o2.order_id
    assert trades[0].price == 100.0


def test_time_priority(engine):
    o1, _ = engine.submit(Side.SELL, OrderType.LIMIT, 100.0, 50)
    o2, _ = engine.submit(Side.SELL, OrderType.LIMIT, 100.0, 50)
    _, trades = engine.submit(Side.BUY, OrderType.MARKET, quantity=60)
    assert trades[0].resting_order_id == o1.order_id
    assert trades[0].quantity == 50
    assert trades[1].resting_order_id == o2.order_id
    assert trades[1].quantity == 10


def test_cancel(engine):
    o, _ = engine.submit(Side.SELL, OrderType.LIMIT, 100.0, 50)
    assert engine.cancel(o.order_id)
    assert o.status == OrderStatus.CANCELLED
    assert engine.ask_count == 0
    assert not engine.cancel(o.order_id)
    assert not engine.cancel(999)


def test_modify_qty_down_keeps_priority(engine):
    o1, _ = engine.submit(Side.SELL, OrderType.LIMIT, 100.0, 50)
    o2, _ = engine.submit(Side.SELL, OrderType.LIMIT, 100.0, 50)
    engine.modify(o1.order_id, new_qty=20)
    assert o1.remaining_qty == 20
    _, trades = engine.submit(Side.BUY, OrderType.MARKET, quantity=30)
    assert trades[0].resting_order_id == o1.order_id
    assert trades[0].quantity == 20
    assert trades[1].resting_order_id == o2.order_id


def test_modify_qty_up_loses_priority(engine):
    o1, _ = engine.submit(Side.SELL, OrderType.LIMIT, 100.0, 50)
    o2, _ = engine.submit(Side.SELL, OrderType.LIMIT, 100.0, 50)
    engine.modify(o1.order_id, new_qty=60)
    _, trades = engine.submit(Side.BUY, OrderType.MARKET, quantity=40)
    assert trades[0].resting_order_id == o2.order_id


def test_modify_price_loses_priority(engine):
    o1, _ = engine.submit(Side.SELL, OrderType.LIMIT, 100.0, 50)
    o2, _ = engine.submit(Side.SELL, OrderType.LIMIT, 100.0, 50)
    engine.modify(o1.order_id, new_price=100.0)
    _, trades = engine.submit(Side.BUY, OrderType.MARKET, quantity=30)
    assert trades[0].resting_order_id == o2.order_id


def test_snapshot(engine):
    engine.submit(Side.BUY, OrderType.LIMIT, 99.0, 50)
    engine.submit(Side.SELL, OrderType.LIMIT, 101.0, 50)
    snap = engine.snapshot()
    assert snap['best_bid'] == 99.0
    assert snap['best_ask'] == 101.0
    assert snap['spread'] == 2.0


def test_empty_snapshot(engine):
    snap = engine.snapshot()
    assert snap['best_bid'] is None
    assert snap['best_ask'] is None
    assert snap['bids'] == []


def test_submit_validation(engine):
    with pytest.raises(ValueError):
        engine.submit(Side.BUY, OrderType.LIMIT, 100.0, 0)
    with pytest.raises(ValueError):
        engine.submit(Side.BUY, OrderType.LIMIT, None, 100)


def test_ids_increase(engine):
    o1, _ = engine.submit(Side.BUY, OrderType.LIMIT, 100.0, 10)
    o2, _ = engine.submit(Side.BUY, OrderType.LIMIT, 100.0, 10)
    assert o2.order_id > o1.order_id


def test_multi_level_sweep(engine):
    engine.submit(Side.SELL, OrderType.LIMIT, 100.0, 30)
    engine.submit(Side.SELL, OrderType.LIMIT, 101.0, 30)
    engine.submit(Side.SELL, OrderType.LIMIT, 102.0, 30)
    _, trades = engine.submit(Side.BUY, OrderType.MARKET, quantity=70)
    assert len(trades) == 3
    assert sum(t.quantity for t in trades) == 70
    assert trades[0].price == 100.0
    assert trades[1].price == 101.0
    assert trades[2].price == 102.0
