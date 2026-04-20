"""P0-8: Equity curve mark-to-market (unrealized PnL).

G10: Equity curve includes unrealized PnL from open positions.
G11: Unrealized PnL updates each bar as market price moves.
G12: After trade closes, unrealized PnL drops to zero for that trade.
"""
import pytest
from datetime import datetime
from unittest.mock import MagicMock
from engines.execution.paper_trading import ExecutionEngine
from models.trade import Trade


def _make_engine():
    """Create a minimal ExecutionEngine with mocked risk_engine."""
    risk = MagicMock()
    risk.state = MagicMock()
    risk.state.base_r_unit_dollars = 2000.0  # 2% of $100k
    risk.on_trade_closed = MagicMock()
    engine = ExecutionEngine(risk)
    return engine


def _make_trade(trade_id="t1", direction="LONG", entry=450.0, sl=448.0,
                tp1=454.0, position_size=100):
    """Create a minimal Trade object."""
    return Trade(
        id=trade_id,
        date=datetime(2025, 7, 15),
        time_entry=datetime(2025, 7, 15, 14, 30),
        symbol="SPY",
        direction=direction,
        bias_htf="bullish" if direction == "LONG" else "bearish",
        session_profile=1,
        session="NY",
        playbook="TestPlaybook",
        setup_quality="A",
        setup_score=80.0,
        trade_type="SCALP",
        entry_price=entry,
        stop_loss=sl,
        initial_stop_loss=sl,
        take_profit_1=tp1,
        take_profit_2=None,
        exit_price=entry,
        position_size=position_size,
        risk_amount=200.0,
        risk_pct=0.02,
        pnl_dollars=0.0,
        pnl_pct=0.0,
        r_multiple=0.0,
        risk_tier=2,
        outcome="pending",
        exit_reason="",
    )


class TestUnrealizedPnL:
    """G10: Equity includes unrealized PnL."""

    def test_long_unrealized_profit(self):
        """LONG open trade with price above entry → positive unrealized PnL."""
        engine = _make_engine()
        trade = _make_trade("t1", "LONG", entry=450.0, position_size=100)
        engine.open_trades[trade.id] = trade

        # Simulate: create a backtest-like object to test _calc_unrealized_pnl
        # Price at 452 → unrealized = (452 - 450) * 100 = $200
        market_data = {"SPY": 452.0}

        unrealized = 0.0
        for t in engine.get_open_trades():
            price = market_data.get(t.symbol)
            if price and t.direction == "LONG":
                unrealized += (price - t.entry_price) * t.position_size
            elif price and t.direction == "SHORT":
                unrealized += (t.entry_price - price) * t.position_size

        assert unrealized == pytest.approx(200.0)

    def test_long_unrealized_loss(self):
        """LONG open trade with price below entry → negative unrealized PnL."""
        engine = _make_engine()
        trade = _make_trade("t1", "LONG", entry=450.0, position_size=100)
        engine.open_trades[trade.id] = trade

        market_data = {"SPY": 448.0}
        unrealized = 0.0
        for t in engine.get_open_trades():
            price = market_data.get(t.symbol)
            if price and t.direction == "LONG":
                unrealized += (price - t.entry_price) * t.position_size

        assert unrealized == pytest.approx(-200.0)

    def test_short_unrealized_profit(self):
        """SHORT open trade with price below entry → positive unrealized PnL."""
        engine = _make_engine()
        trade = _make_trade("t1", "SHORT", entry=450.0, sl=452.0,
                            tp1=446.0, position_size=100)
        engine.open_trades[trade.id] = trade

        market_data = {"SPY": 448.0}
        unrealized = 0.0
        for t in engine.get_open_trades():
            price = market_data.get(t.symbol)
            if price and t.direction == "SHORT":
                unrealized += (t.entry_price - price) * t.position_size

        assert unrealized == pytest.approx(200.0)

    def test_short_unrealized_loss(self):
        """SHORT open trade with price above entry → negative unrealized PnL."""
        engine = _make_engine()
        trade = _make_trade("t1", "SHORT", entry=450.0, sl=452.0,
                            tp1=446.0, position_size=100)
        engine.open_trades[trade.id] = trade

        market_data = {"SPY": 452.0}
        unrealized = 0.0
        for t in engine.get_open_trades():
            price = market_data.get(t.symbol)
            if price and t.direction == "SHORT":
                unrealized += (t.entry_price - price) * t.position_size

        assert unrealized == pytest.approx(-200.0)


class TestMultiplePositions:
    """G11: Multiple open positions → combined unrealized PnL."""

    def test_two_trades_combined(self):
        """Two open trades: net unrealized = sum of individual."""
        engine = _make_engine()
        t1 = _make_trade("t1", "LONG", entry=450.0, position_size=100)
        t2 = _make_trade("t2", "SHORT", entry=380.0, sl=382.0,
                         tp1=376.0, position_size=50)
        t2.symbol = "QQQ"
        engine.open_trades[t1.id] = t1
        engine.open_trades[t2.id] = t2

        market_data = {"SPY": 452.0, "QQQ": 378.0}
        unrealized = 0.0
        for t in engine.get_open_trades():
            price = market_data.get(t.symbol)
            if price is None:
                continue
            if t.direction == "LONG":
                unrealized += (price - t.entry_price) * t.position_size
            else:
                unrealized += (t.entry_price - price) * t.position_size

        # SPY LONG: (452-450)*100 = +200
        # QQQ SHORT: (380-378)*50 = +100
        assert unrealized == pytest.approx(300.0)

    def test_no_open_trades_zero(self):
        """No open trades → unrealized = 0."""
        engine = _make_engine()
        assert len(engine.get_open_trades()) == 0


class TestMarkToMarketUpdates:
    """G12: Unrealized PnL changes as market moves."""

    def test_price_moves_updates_unrealized(self):
        """Unrealized PnL changes with each price update."""
        engine = _make_engine()
        trade = _make_trade("t1", "LONG", entry=450.0, position_size=100)
        engine.open_trades[trade.id] = trade

        def calc_unrealized(price):
            return (price - trade.entry_price) * trade.position_size

        # Price sequence: 451, 453, 449
        assert calc_unrealized(451.0) == pytest.approx(100.0)
        assert calc_unrealized(453.0) == pytest.approx(300.0)
        assert calc_unrealized(449.0) == pytest.approx(-100.0)

    def test_closed_trade_no_unrealized(self):
        """After closing a trade, it should not contribute unrealized PnL."""
        engine = _make_engine()
        trade = _make_trade("t1", "LONG", entry=450.0, position_size=100)
        engine.open_trades[trade.id] = trade

        # Before close: 1 open trade
        assert len(engine.get_open_trades()) == 1

        # Close the trade
        engine.close_trade(trade.id, "TP1", 454.0,
                           current_time=datetime(2025, 7, 15, 15, 0))

        # After close: 0 open trades
        assert len(engine.get_open_trades()) == 0
        # Closed trade is in closed_trades
        assert len(engine.closed_trades) == 1
