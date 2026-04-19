"""P0-1 / P0-3: Intra-bar SL/TP checks using full candle OHLC.

Tests verify that update_open_trades() correctly uses candle_low (LONG)
and candle_high (SHORT) for SL detection, and candle_high (LONG) /
candle_low (SHORT) for TP detection.
"""
import pytest
from datetime import datetime
from unittest.mock import MagicMock
from models.trade import Trade
from engines.execution.paper_trading import ExecutionEngine


def _make_engine():
    """Create a minimal ExecutionEngine with mocked risk_engine."""
    risk = MagicMock()
    risk.state = MagicMock()
    risk.state.base_r_unit_dollars = 100.0
    risk.on_trade_closed = MagicMock()
    engine = ExecutionEngine(risk)
    return engine


def _make_trade(direction="LONG", entry=450.0, sl=448.0, tp1=454.0, tp2=None):
    """Create a minimal Trade object."""
    return Trade(
        id="test-trade-1",
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
        trade_type="DAILY",
        entry_price=entry,
        stop_loss=sl,
        initial_stop_loss=sl,
        take_profit_1=tp1,
        take_profit_2=tp2,
        exit_price=entry,  # placeholder
        position_size=100,
        risk_amount=200.0,
        risk_pct=0.02,
        pnl_dollars=0.0,
        pnl_pct=0.0,
        r_multiple=0.0,
        outcome="pending",
        exit_reason="",
    )


def _get_closed(engine):
    """Get the last closed trade from engine."""
    assert len(engine.closed_trades) > 0, "No trades were closed"
    return engine.closed_trades[-1]


def _ohlc(o, h, l, c):
    """Helper to build OHLC dict for market_data."""
    return {'open': o, 'high': h, 'low': l, 'close': c}


class TestIntrabarSLCheck:
    """SL is checked using candle_low (LONG) / candle_high (SHORT)."""

    def test_long_sl_hit_via_candle_low(self):
        """LONG: candle_low <= SL triggers SL even if close > SL."""
        engine = _make_engine()
        trade = _make_trade("LONG", entry=450.0, sl=448.0, tp1=454.0)
        engine.open_trades[trade.id] = trade

        # Close is above SL but low dipped below SL
        engine.update_open_trades(
            market_data={"SPY": _ohlc(449.5, 450.0, 447.0, 449.0)},
            current_time=datetime(2025, 7, 15, 14, 35),
        )
        closed = _get_closed(engine)
        assert closed.exit_reason == "SL"
        assert closed.exit_price == 448.0  # closes at SL level

    def test_long_sl_not_hit_when_low_above_sl(self):
        """LONG: candle_low > SL means no SL hit."""
        engine = _make_engine()
        trade = _make_trade("LONG", entry=450.0, sl=448.0, tp1=454.0)
        engine.open_trades[trade.id] = trade

        engine.update_open_trades(
            market_data={"SPY": _ohlc(449.5, 451.0, 448.5, 450.0)},
            current_time=datetime(2025, 7, 15, 14, 35),
        )
        assert len(engine.closed_trades) == 0

    def test_short_sl_hit_via_candle_high(self):
        """SHORT: candle_high >= SL triggers SL even if close < SL."""
        engine = _make_engine()
        trade = _make_trade("SHORT", entry=450.0, sl=452.0, tp1=446.0)
        engine.open_trades[trade.id] = trade

        engine.update_open_trades(
            market_data={"SPY": _ohlc(450.5, 453.0, 450.0, 451.0)},
            current_time=datetime(2025, 7, 15, 14, 35),
        )
        closed = _get_closed(engine)
        assert closed.exit_reason == "SL"
        assert closed.exit_price == 452.0

    def test_short_sl_not_hit_when_high_below_sl(self):
        """SHORT: candle_high < SL means no SL hit."""
        engine = _make_engine()
        trade = _make_trade("SHORT", entry=450.0, sl=452.0, tp1=446.0)
        engine.open_trades[trade.id] = trade

        engine.update_open_trades(
            market_data={"SPY": _ohlc(450.0, 451.5, 449.0, 450.5)},
            current_time=datetime(2025, 7, 15, 14, 35),
        )
        assert len(engine.closed_trades) == 0


class TestIntrabarTPCheck:
    """TP is checked using candle_high (LONG) / candle_low (SHORT)."""

    def test_long_tp1_hit_via_candle_high(self):
        """LONG: candle_high >= TP1 triggers TP even if close < TP1."""
        engine = _make_engine()
        trade = _make_trade("LONG", entry=450.0, sl=448.0, tp1=454.0)
        engine.open_trades[trade.id] = trade

        # High reached TP but close didn't
        engine.update_open_trades(
            market_data={"SPY": _ohlc(451.0, 455.0, 450.5, 452.0)},
            current_time=datetime(2025, 7, 15, 14, 35),
        )
        closed = _get_closed(engine)
        assert closed.exit_reason in ("TP1", "TP2")
        assert closed.exit_price == 454.0

    def test_short_tp1_hit_via_candle_low(self):
        """SHORT: candle_low <= TP1 triggers TP even if close > TP1."""
        engine = _make_engine()
        trade = _make_trade("SHORT", entry=450.0, sl=452.0, tp1=446.0)
        engine.open_trades[trade.id] = trade

        engine.update_open_trades(
            market_data={"SPY": _ohlc(449.0, 450.0, 445.0, 448.0)},
            current_time=datetime(2025, 7, 15, 14, 35),
        )
        closed = _get_closed(engine)
        assert closed.exit_reason in ("TP1", "TP2")
        assert closed.exit_price == 446.0


class TestSLTPBothHit:
    """When both SL and TP are hit in same bar, SL is checked first (conservative)."""

    def test_long_both_hit_sl_wins(self):
        """LONG: both SL and TP hit in same bar, SL checked first."""
        engine = _make_engine()
        trade = _make_trade("LONG", entry=450.0, sl=448.0, tp1=454.0)
        engine.open_trades[trade.id] = trade

        engine.update_open_trades(
            market_data={"SPY": _ohlc(449.0, 455.0, 447.0, 451.0)},
            current_time=datetime(2025, 7, 15, 14, 35),
        )
        closed = _get_closed(engine)
        assert closed.exit_reason == "SL"

    def test_short_both_hit_sl_wins(self):
        """SHORT: both SL and TP hit in same bar, SL checked first."""
        engine = _make_engine()
        trade = _make_trade("SHORT", entry=450.0, sl=452.0, tp1=446.0)
        engine.open_trades[trade.id] = trade

        engine.update_open_trades(
            market_data={"SPY": _ohlc(451.0, 453.0, 445.0, 449.0)},
            current_time=datetime(2025, 7, 15, 14, 35),
        )
        closed = _get_closed(engine)
        assert closed.exit_reason == "SL"

    def test_only_sl_hit(self):
        """Only SL hit (TP not reached)."""
        engine = _make_engine()
        trade = _make_trade("LONG", entry=450.0, sl=448.0, tp1=454.0)
        engine.open_trades[trade.id] = trade

        engine.update_open_trades(
            market_data={"SPY": _ohlc(449.5, 450.0, 447.0, 448.5)},
            current_time=datetime(2025, 7, 15, 14, 35),
        )
        closed = _get_closed(engine)
        assert closed.exit_reason == "SL"
        assert closed.exit_price == 448.0

    def test_only_tp_hit(self):
        """Only TP hit (SL not reached)."""
        engine = _make_engine()
        trade = _make_trade("LONG", entry=450.0, sl=448.0, tp1=454.0)
        engine.open_trades[trade.id] = trade

        engine.update_open_trades(
            market_data={"SPY": _ohlc(451.0, 455.0, 450.5, 454.5)},
            current_time=datetime(2025, 7, 15, 14, 35),
        )
        closed = _get_closed(engine)
        assert closed.exit_reason in ("TP1", "TP2")
        assert closed.exit_price == 454.0


class TestBackwardCompatibility:
    """market_data as plain float (legacy format) still works."""

    def test_plain_float_market_data(self):
        """Legacy format: {symbol: float} still works."""
        engine = _make_engine()
        trade = _make_trade("LONG", entry=450.0, sl=448.0, tp1=454.0)
        engine.open_trades[trade.id] = trade

        # Legacy format: plain float
        engine.update_open_trades(
            market_data={"SPY": 447.0},
            current_time=datetime(2025, 7, 15, 14, 35),
        )
        closed = _get_closed(engine)
        assert closed.exit_reason == "SL"
