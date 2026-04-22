"""Phase W.1 — shared entry_gates contract.

Verifies that engines.execution.entry_gates.check_entry_confirmation is a pure
function callable by both backtest and paper/live. The separate end-to-end test
test_entry_confirmation_gate.py covers the backtest wiring; this one locks the
function's contract so paper_trading can rely on identical semantics.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import pytest


def _backend_dir() -> Path:
    return Path(__file__).parent.parent


sys.path.insert(0, str(_backend_dir()))


from engines.execution.entry_gates import (  # noqa: E402
    GATE_REASON_NO_CANDLES,
    GATE_REASON_NO_COMMIT,
    check_entry_confirmation,
)


@dataclass
class _Candle:
    close: float


@dataclass
class _Setup:
    entry_price: float
    direction: str
    symbol: str = "SPY"


class _Playbook:
    def __init__(self, enabled: bool = True, bps: float = 2.0):
        self.require_close_above_trigger = enabled
        self.entry_buffer_bps = bps


def test_gate_off_bypasses():
    pb = _Playbook(enabled=False)
    setup = _Setup(entry_price=500.0, direction="LONG")
    res = check_entry_confirmation(pb, setup, None)
    assert res.passed is True
    assert res.reason is None


def test_gate_on_no_candles_rejects_closed():
    pb = _Playbook(enabled=True)
    setup = _Setup(entry_price=500.0, direction="LONG")
    res = check_entry_confirmation(pb, setup, None)
    assert res.passed is False
    assert res.reason == GATE_REASON_NO_CANDLES


def test_gate_on_one_candle_rejects_closed():
    pb = _Playbook(enabled=True)
    setup = _Setup(entry_price=500.0, direction="LONG")
    res = check_entry_confirmation(pb, setup, [_Candle(close=500.0)])
    assert res.passed is False
    assert res.reason == GATE_REASON_NO_CANDLES


def test_long_committed_passes():
    pb = _Playbook(enabled=True, bps=2.0)  # buffer = 500 * 2/10000 = 0.10
    setup = _Setup(entry_price=500.0, direction="LONG")
    # close_now - close_prev = 0.20 > 0.10 buffer
    candles = [_Candle(close=500.00), _Candle(close=500.20)]
    res = check_entry_confirmation(pb, setup, candles)
    assert res.passed is True
    assert res.reason is None
    assert res.buffer_abs == pytest.approx(0.10)


def test_long_not_committed_rejects():
    pb = _Playbook(enabled=True, bps=2.0)  # buffer 0.10
    setup = _Setup(entry_price=500.0, direction="LONG")
    # move 0.05 < buffer 0.10 → reject
    candles = [_Candle(close=500.00), _Candle(close=500.05)]
    res = check_entry_confirmation(pb, setup, candles)
    assert res.passed is False
    assert res.reason == GATE_REASON_NO_COMMIT


def test_short_committed_passes():
    pb = _Playbook(enabled=True, bps=2.0)  # buffer 0.10
    setup = _Setup(entry_price=500.0, direction="SHORT")
    # close_now < close_prev - buffer → 499.85 < 500.00 - 0.10 = 499.90
    candles = [_Candle(close=500.00), _Candle(close=499.85)]
    res = check_entry_confirmation(pb, setup, candles)
    assert res.passed is True


def test_short_not_committed_rejects():
    pb = _Playbook(enabled=True, bps=2.0)
    setup = _Setup(entry_price=500.0, direction="SHORT")
    candles = [_Candle(close=500.00), _Candle(close=499.95)]
    res = check_entry_confirmation(pb, setup, candles)
    assert res.passed is False
    assert res.reason == GATE_REASON_NO_COMMIT


def test_unknown_direction_rejects():
    pb = _Playbook(enabled=True)
    setup = _Setup(entry_price=500.0, direction="")
    candles = [_Candle(close=500.00), _Candle(close=501.00)]
    res = check_entry_confirmation(pb, setup, candles)
    assert res.passed is False
    assert res.reason == GATE_REASON_NO_COMMIT


def test_paper_execution_engine_hook_matches_backtest_gate():
    """ExecutionEngine.check_entry_confirmation_gate delegates to the same
    shared function as the backtest path. Locking this makes 'même cerveau'
    real: if the gate logic diverges, this test fails."""
    from engines.execution.paper_trading import ExecutionEngine

    class _StubPlaybookLoader:
        def __init__(self, pb):
            self._pb = pb

        def get_playbook_by_name(self, name):
            return self._pb

    pb = _Playbook(enabled=True, bps=2.0)  # buffer 0.10 on 500.0

    # Build the engine without invoking __init__ (avoids risk_engine plumbing).
    eng = object.__new__(ExecutionEngine)
    eng.playbook_loader = _StubPlaybookLoader(pb)

    class _PaperSetup:
        def __init__(self, direction, playbook_name="Engulfing_Bar_V056"):
            self.entry_price = 500.0
            self.direction = direction
            self.symbol = "SPY"
            self.playbook_name = playbook_name
            self.playbook_matches = []

    committed = [_Candle(close=500.00), _Candle(close=500.25)]
    not_committed = [_Candle(close=500.00), _Candle(close=500.05)]

    # Same input → same verdict across backtest and paper callers.
    direct_pass = check_entry_confirmation(pb, _PaperSetup("LONG"), committed)
    paper_pass = eng.check_entry_confirmation_gate(_PaperSetup("LONG"), committed)
    assert direct_pass.passed == paper_pass.passed is True

    direct_reject = check_entry_confirmation(pb, _PaperSetup("LONG"), not_committed)
    paper_reject = eng.check_entry_confirmation_gate(_PaperSetup("LONG"), not_committed)
    assert direct_reject.passed == paper_reject.passed is False
    assert direct_reject.reason == paper_reject.reason == GATE_REASON_NO_COMMIT

    # Missing playbook → pass-through (don't break paper on unknown setups).
    eng2 = object.__new__(ExecutionEngine)
    eng2.playbook_loader = _StubPlaybookLoader(None)
    res = eng2.check_entry_confirmation_gate(_PaperSetup("LONG"), not_committed)
    assert res.passed is True
