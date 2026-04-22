"""
Phase C.3 — Entry confirmation gate sanity.

Verifies that when a playbook has `require_close_above_trigger: true`, the gate
rejects setups on 1m bars that did NOT commit past prior close by entry_buffer_bps,
and accepts setups on bars that DID commit. Flag-off playbooks bypass the gate.

The harness exercises the _execute_setup path with minimal plumbing — we inject
fake 1m candles via a stub tf_aggregator, stub out risk_engine + execution_engine
to isolate the gate logic from other reject reasons.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import pytest


def _backend_dir() -> Path:
    return Path(__file__).parent.parent


sys.path.insert(0, str(_backend_dir()))


@dataclass
class _FakeCandle:
    close: float
    timestamp: datetime | None = None


class _FakeTFA:
    def __init__(self, candles_by_symbol: Dict[str, List[_FakeCandle]]):
        self._c = candles_by_symbol

    def get_candles(self, symbol: str, tf: str):
        return self._c.get(symbol, [])


class _FakePlaybook:
    def __init__(self, require_close_above_trigger: bool, entry_buffer_bps: float):
        self.require_close_above_trigger = require_close_above_trigger
        self.entry_buffer_bps = entry_buffer_bps


class _FakeLoader:
    def __init__(self, pbs: Dict[str, _FakePlaybook]):
        self._p = pbs

    def get_playbook_by_name(self, name: str):
        return self._p.get(name)


class _FakeSetupEngine:
    def __init__(self, loader: _FakeLoader):
        self.playbook_loader = loader


class _FakeRisk:
    def can_take_setup(self, setup):
        return {"allowed": True}

    def check_cooldown_and_session_limit(self, setup, current_time, session_key):
        return True, "ok"

    def check_trades_cap(self, symbol, date):
        return True, "ok"

    def calculate_position_size(self, setup):
        class _P:
            valid = True
            risk_tier = 1
            risk_amount = 100.0
            reason = None
        return _P()

    class _S:
        current_risk_pct = 0.01
        trading_mode = "AGGRESSIVE"

    state = _S()

    def increment_trades_count(self, *a, **k):
        pass

    def record_trade_for_cooldown(self, *a, **k):
        pass


class _FakeExec:
    def place_order(self, setup, risk_allocation, current_time=None):
        # Mimic successful order
        return {"success": True}


@dataclass
class _FakeSetup:
    symbol: str = "SPY"
    direction: str = "LONG"
    entry_price: float = 100.0
    playbook_name: str = "BOS_Scalp_1m"
    quality: str = "A"


def _make_engine_shell(candles: Dict[str, List[_FakeCandle]], pbs: Dict[str, _FakePlaybook]):
    """Build a minimal object that has exactly the attributes _execute_setup uses."""
    # Import lazily to avoid picking up heavy engine state at module load.
    from backtest.engine import BacktestEngine  # type: ignore

    # Construct a thin dummy by using __new__ to skip __init__
    eng = BacktestEngine.__new__(BacktestEngine)
    # Minimum attributes referenced in the gate path
    eng.debug_counts = {
        "trades_open_attempted_total": 0,
        "trades_opened_total": 0,
        "setups_detected_total": 0,
        "setups_accepted_total": 0,
        "setups_rejected_total": 0,
        "setups_rejected_by_mode": 0,
        "setups_rejected_by_trade_types": 0,
    }
    eng._stop_run_triggered = False
    eng._stop_run_time = None
    eng.setup_engine = _FakeSetupEngine(_FakeLoader(pbs))
    eng.tf_aggregator = _FakeTFA(candles)
    eng.risk_engine = _FakeRisk()
    eng.execution_engine = _FakeExec()
    # Counters referenced later in _execute_setup
    eng.blocked_by_cooldown = 0
    eng.blocked_by_cooldown_details = {}
    eng.blocked_by_session_limit = 0
    eng.blocked_by_session_limit_details = {}
    eng._last_session_label = {}
    eng._session_states = {}
    eng._session_ranges_history = {}

    # Monkey-patch the reject counter to a no-op
    eng._increment_reject_reason = lambda reason: None

    # Monkey-patch snapshot to no-op (uses symbol-specific state we don't have)
    eng._get_inter_session_context_snapshot = lambda *a, **k: {}

    return eng


def test_gate_rejects_when_not_committed_long():
    """LONG setup, close_now == close_prev → not committed → reject."""
    candles = {"SPY": [_FakeCandle(100.0), _FakeCandle(100.0)]}
    pbs = {"BOS_Scalp_1m": _FakePlaybook(True, 2.0)}
    eng = _make_engine_shell(candles, pbs)
    setup = _FakeSetup(direction="LONG", playbook_name="BOS_Scalp_1m", entry_price=100.0)

    result = eng._execute_setup(setup, datetime.now(timezone.utc))
    assert result is False, "gate should reject when close_now == close_prev"
    stats = eng.debug_counts["entry_confirm_stats"]["BOS_Scalp_1m"]
    assert stats["checked"] == 1
    assert stats["rejected_no_commit"] == 1
    assert stats["passed"] == 0


def test_gate_accepts_when_committed_long():
    """LONG setup, close_now clearly > close_prev + buffer → accept."""
    # buffer = 100 * 2/10000 = 0.02 ; close_now 100.10 > 100.00 + 0.02
    candles = {"SPY": [_FakeCandle(100.0), _FakeCandle(100.10)]}
    pbs = {"BOS_Scalp_1m": _FakePlaybook(True, 2.0)}
    eng = _make_engine_shell(candles, pbs)
    setup = _FakeSetup(direction="LONG", playbook_name="BOS_Scalp_1m", entry_price=100.0)

    result = eng._execute_setup(setup, datetime.now(timezone.utc))
    # The gate passes; downstream fakes return success
    stats = eng.debug_counts["entry_confirm_stats"]["BOS_Scalp_1m"]
    assert stats["passed"] == 1
    assert stats["rejected_no_commit"] == 0


def test_gate_rejects_when_committed_wrong_direction_short():
    """SHORT setup, close_now > close_prev → wrong direction, reject."""
    candles = {"SPY": [_FakeCandle(100.0), _FakeCandle(100.10)]}
    pbs = {"BOS_Scalp_1m": _FakePlaybook(True, 2.0)}
    eng = _make_engine_shell(candles, pbs)
    setup = _FakeSetup(direction="SHORT", playbook_name="BOS_Scalp_1m", entry_price=100.0)

    result = eng._execute_setup(setup, datetime.now(timezone.utc))
    assert result is False
    stats = eng.debug_counts["entry_confirm_stats"]["BOS_Scalp_1m"]
    assert stats["rejected_no_commit"] == 1


def test_gate_off_bypasses_entirely():
    """Flag off → no gate stats recorded, no reject from gate."""
    candles = {"SPY": [_FakeCandle(100.0), _FakeCandle(100.0)]}
    pbs = {"Engulfing_Bar_V056": _FakePlaybook(False, 2.0)}
    eng = _make_engine_shell(candles, pbs)
    setup = _FakeSetup(direction="LONG", playbook_name="Engulfing_Bar_V056", entry_price=100.0)

    eng._execute_setup(setup, datetime.now(timezone.utc))
    assert "entry_confirm_stats" not in eng.debug_counts, \
        "Gate should not record stats when flag off"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
