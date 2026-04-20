"""P0-4 / P0-5: Concurrent positions cap + capital reservation + max open risk.

G5: Never >MAX_CONCURRENT trades open.
G6: Trade refused if committed_capital > buying_power.
G7: Trade refused if sum open R > MAX_OPEN_RISK_R.
"""
import pytest
from datetime import date
from unittest.mock import MagicMock
from models.risk import RiskEngineState
from engines.risk_engine import (
    RiskEngine,
    MAX_CONCURRENT_POSITIONS_GLOBAL,
    MAX_CONCURRENT_POSITIONS_PER_SYMBOL,
    MAX_OPEN_RISK_R,
)


def _make_risk_engine(balance=100_000.0):
    """Create a RiskEngine with given balance."""
    engine = RiskEngine(initial_capital=balance)
    engine.state.account_balance = balance
    engine.state.peak_balance = balance
    engine.state.base_r_unit_dollars = balance * 0.02  # 2% = $2000 per R
    return engine


def _make_setup(symbol="SPY", direction="LONG", entry=450.0, sl=448.0, tp1=454.0):
    """Create a minimal Setup-like mock."""
    s = MagicMock()
    s.symbol = symbol
    s.direction = direction
    s.entry_price = entry
    s.stop_loss = sl
    s.take_profit_1 = tp1
    s.trade_type = "SCALP"
    s.playbook_name = "TestPlaybook"
    s.quality = "A"
    return s


def _fake_trade(symbol="SPY", entry=450.0, position_size=100):
    """Create a minimal trade-like object for on_trade_opened/closed."""
    t = MagicMock()
    t.symbol = symbol
    t.entry_price = entry
    t.position_size = position_size
    t.direction = "LONG"
    t.trade_type = "SCALP"
    t.playbook = "TestPlaybook"
    t.risk_amount = 200.0
    t.risk_tier = 2
    t.pnl_dollars = 0.0
    t.r_multiple = 0.0
    return t


class TestConcurrentPositionsGlobal:
    """G5: Never > MAX_CONCURRENT trades open."""

    def test_blocks_at_max_global(self):
        """After MAX_CONCURRENT opens, next check_daily_limits should block."""
        engine = _make_risk_engine()

        # Open MAX_CONCURRENT trades
        for i in range(MAX_CONCURRENT_POSITIONS_GLOBAL):
            t = _fake_trade(symbol=f"SYM{i}")
            engine.on_trade_opened(t)

        assert engine.state.open_positions_count == MAX_CONCURRENT_POSITIONS_GLOBAL

        # Next trade should be blocked
        result = engine.check_daily_limits()
        assert result["trading_allowed"] is False
        assert "concurrent" in result["reason"].lower() or "Max" in result["reason"]

    def test_allows_after_close(self):
        """Closing enough trades should allow a new one."""
        engine = _make_risk_engine()

        trades = []
        for i in range(3):  # 3 trades at tier=2 = 6R = max
            t = _fake_trade(symbol=f"SYM{i}")
            engine.on_trade_opened(t)
            trades.append(t)

        # At 3 open, risk = 6R → blocked
        result = engine.check_daily_limits()
        assert result["trading_allowed"] is False

        # Close one → 2 open, risk = 4R → allowed
        engine.on_trade_closed(trades[0])
        assert engine.state.open_positions_count == 2

        result = engine.check_daily_limits()
        assert result["trading_allowed"] is True, f"Blocked with 2 open: {result['reason']}"


class TestConcurrentPositionsPerSymbol:
    """G5 (per-symbol): Never > MAX_PER_SYMBOL trades on same symbol."""

    def test_blocks_same_symbol(self):
        """After MAX_PER_SYMBOL opens on SPY, next SPY should be blocked."""
        engine = _make_risk_engine()

        for i in range(MAX_CONCURRENT_POSITIONS_PER_SYMBOL):
            t = _fake_trade(symbol="SPY")
            engine.on_trade_opened(t)

        # check_trades_cap checks per-symbol
        allowed, reason = engine.check_trades_cap("SPY", date.today())
        assert allowed is False
        assert "SPY" in reason or "concurrent" in reason.lower()

    def test_allows_different_symbol(self):
        """MAX_PER_SYMBOL on SPY should not block QQQ."""
        engine = _make_risk_engine()

        for i in range(MAX_CONCURRENT_POSITIONS_PER_SYMBOL):
            t = _fake_trade(symbol="SPY")
            engine.on_trade_opened(t)

        allowed, reason = engine.check_trades_cap("QQQ", date.today())
        # Should be allowed (QQQ has 0 open)
        assert allowed is True


class TestCapitalReservation:
    """G6: Trade refused if committed_capital > buying_power."""

    def test_capital_exhaustion(self):
        """When committed capital exceeds available, sizing should return 0 or invalid."""
        engine = _make_risk_engine(balance=50_000.0)

        # Commit most of the capital
        t1 = _fake_trade(symbol="SPY", entry=450.0, position_size=100)
        engine.on_trade_opened(t1)
        # Committed = 100 * 450 = $45,000

        assert engine.state.committed_capital == pytest.approx(45_000.0)

        # Try to size a new trade — available capital should be ~$5,000
        setup = _make_setup(symbol="QQQ", entry=450.0, sl=448.0)
        result = engine.calculate_position_size(setup)

        # With $5,000 available and entry at $450, max ~11 shares
        # But 2R risk = $2,000 (2% of $50k), risk_distance = $2
        # Shares = 2000/2 = 1000 → capped by available capital
        # Available $5,000 / $450 = ~11 shares
        assert result.position_size <= 12  # Capped by available capital

    def test_committed_tracks_correctly(self):
        """Verify committed_capital increments on open, decrements on close."""
        engine = _make_risk_engine(balance=100_000.0)

        t1 = _fake_trade(symbol="SPY", entry=450.0, position_size=50)
        engine.on_trade_opened(t1)
        assert engine.state.committed_capital == pytest.approx(22_500.0)

        t2 = _fake_trade(symbol="QQQ", entry=380.0, position_size=30)
        engine.on_trade_opened(t2)
        assert engine.state.committed_capital == pytest.approx(22_500.0 + 11_400.0)

        engine.on_trade_closed(t1)
        assert engine.state.committed_capital == pytest.approx(11_400.0)

        engine.on_trade_closed(t2)
        assert engine.state.committed_capital == pytest.approx(0.0)


class TestMaxOpenRisk:
    """G7: Trade refused if sum open R > MAX_OPEN_RISK_R."""

    def test_blocks_at_max_risk(self):
        """With tier=2 and 3 trades open, risk = 6R → should block."""
        engine = _make_risk_engine()
        # tier=2 (default), 3 trades = 6R = MAX_OPEN_RISK_R
        for i in range(3):
            t = _fake_trade(symbol=f"SYM{i}")
            engine.on_trade_opened(t)

        result = engine.check_daily_limits()
        assert result["trading_allowed"] is False
        assert "risk" in result["reason"].lower() or "6.0R" in result["reason"]

    def test_allows_below_max_risk(self):
        """With tier=2 and 2 trades open, risk = 4R < 6R → allowed."""
        engine = _make_risk_engine()
        for i in range(2):
            t = _fake_trade(symbol=f"SYM{i}")
            engine.on_trade_opened(t)

        result = engine.check_daily_limits()
        assert result["trading_allowed"] is True

    def test_tier1_allows_more_trades(self):
        """With tier=1, each trade risks 1R → can have up to 5 before max (5R < 6R)."""
        engine = _make_risk_engine()
        engine.state.risk_tier_state.current_tier = 1
        for i in range(5):
            t = _fake_trade(symbol=f"SYM{i}")
            engine.on_trade_opened(t)

        # 5 trades * 1R = 5R < 6R → should still be allowed
        # BUT hit MAX_CONCURRENT=5 → blocked by concurrent, not risk
        result = engine.check_daily_limits()
        assert result["trading_allowed"] is False
