import pytest
from lob.order import Order, Side, OrderType, OrderStatus
from lob.order_book import OrderBookSide


def _order(oid, side, price, qty):
    return Order(oid, side, OrderType.LIMIT, price, qty, qty, oid)


def test_bid_best_price():
    book = OrderBookSide(Side.BUY)
    book.add(_order(1, Side.BUY, 99.0, 10))
    book.add(_order(2, Side.BUY, 101.0, 10))
    assert book.best_price() == 101.0


def test_ask_best_price():
    book = OrderBookSide(Side.SELL)
    book.add(_order(1, Side.SELL, 101.0, 10))
    book.add(_order(2, Side.SELL, 99.0, 10))
    assert book.best_price() == 99.0


def test_depth():
    book = OrderBookSide(Side.SELL)
    book.add(_order(1, Side.SELL, 100.0, 10))
    book.add(_order(2, Side.SELL, 100.0, 20))
    book.add(_order(3, Side.SELL, 101.0, 30))
    d = book.depth(10)
    assert d[0] == (100.0, 30, 2)
    assert d[1] == (101.0, 30, 1)


def test_remove_order():
    book = OrderBookSide(Side.BUY)
    book.add(_order(1, Side.BUY, 100.0, 10))
    book.add(_order(2, Side.BUY, 100.0, 20))
    book.remove(1)
    assert not book.has(1)
    assert book.has(2)
    assert book.num_orders == 1


def test_remove_empties_level():
    book = OrderBookSide(Side.BUY)
    book.add(_order(1, Side.BUY, 100.0, 10))
    book.remove(1)
    assert book.is_empty()
    assert book.num_levels == 0


def test_volume():
    book = OrderBookSide(Side.BUY)
    book.add(_order(1, Side.BUY, 100.0, 10))
    book.add(_order(2, Side.BUY, 101.0, 20))
    assert book.volume() == 30
