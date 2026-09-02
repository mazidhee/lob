import pytest
from lob.order import Order, Side, OrderType, OrderStatus
from lob.price_level import PriceLevel


def _order(oid, qty):
    return Order(oid, Side.BUY, OrderType.LIMIT, 100.0, qty, qty, oid)


def test_append_and_front():
    pl = PriceLevel(100.0)
    o = _order(1, 50)
    pl.append(o)
    assert pl.front() is o
    assert pl.total_qty == 50
    assert pl.order_count == 1
    assert not pl.is_empty()


def test_fifo_order():
    pl = PriceLevel(100.0)
    orders = [_order(i, 10) for i in range(1, 4)]
    for o in orders:
        pl.append(o)
    assert list(pl) == orders


def test_pop_front_fifo():
    pl = PriceLevel(100.0)
    orders = [_order(i, 10) for i in range(1, 4)]
    for o in orders:
        pl.append(o)
    for expected in orders:
        assert pl.pop_front().order is expected
    assert pl.is_empty()
    assert pl.total_qty == 0


def test_pop_front_empty():
    with pytest.raises(IndexError):
        PriceLevel(100.0).pop_front()


def test_remove_middle():
    pl = PriceLevel(100.0)
    n1 = pl.append(_order(1, 10))
    n2 = pl.append(_order(2, 20))
    n3 = pl.append(_order(3, 30))
    pl.remove(n2)
    assert pl.order_count == 2
    assert pl.total_qty == 40
    assert [o.order_id for o in pl] == [1, 3]


def test_remove_head_and_tail():
    pl = PriceLevel(100.0)
    n1 = pl.append(_order(1, 10))
    n2 = pl.append(_order(2, 20))
    pl.remove(n1)
    assert pl.front().order_id == 2
    pl.remove(n2)
    assert pl.is_empty()


def test_total_qty_consistency():
    pl = PriceLevel(100.0)
    pl.append(_order(1, 50))
    pl.append(_order(2, 30))
    assert pl.total_qty == 80
    pl.pop_front()
    assert pl.total_qty == 30
    pl.pop_front()
    assert pl.total_qty == 0
