from hypothesis import settings
from hypothesis.stateful import RuleBasedStateMachine, rule, initialize, invariant
from hypothesis import strategies as st
from lob.order import Side, OrderType, OrderStatus
from lob.matching_engine import MatchingEngine


class EngineStateMachine(RuleBasedStateMachine):

    def __init__(self):
        super().__init__()
        self.engine = MatchingEngine()

    @initialize()
    def setup(self):
        self.engine = MatchingEngine()

    @rule(
        side=st.sampled_from(Side),
        otype=st.sampled_from(OrderType),
        price=st.floats(1.0, 500.0, allow_nan=False, allow_infinity=False).map(lambda x: round(x, 2)),
        qty=st.integers(1, 5000),
    )
    def add_order(self, side, otype, price, qty):
        if otype == OrderType.MARKET:
            price = None
        self.engine.submit(side, otype, price, qty)

    @rule(oid=st.integers(1, 500))
    def cancel_order(self, oid):
        self.engine.cancel(oid)

    @invariant()
    def no_crossed_book(self):
        bid, ask = self.engine.bbo()
        if bid is not None and ask is not None:
            assert bid < ask

    @invariant()
    def no_negative_qty(self):
        for order in self.engine._orders.values():
            assert order.remaining_qty >= 0

    @invariant()
    def status_consistency(self):
        for order in self.engine._orders.values():
            if order.status == OrderStatus.FILLED:
                assert order.remaining_qty == 0
                assert not self.engine._bids.has(order.order_id)
                assert not self.engine._asks.has(order.order_id)
            elif order.status == OrderStatus.CANCELLED:
                assert not self.engine._bids.has(order.order_id)
                assert not self.engine._asks.has(order.order_id)

    @invariant()
    def fifo_preserved(self):
        for book in [self.engine._bids, self.engine._asks]:
            for key in book._levels:
                prev_ts = -1
                for order in book._levels[key]:
                    assert order.timestamp >= prev_ts
                    prev_ts = order.timestamp


TestEngineProperties = EngineStateMachine.TestCase
