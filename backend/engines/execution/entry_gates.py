"""Shared entry gates callable from both backtest and paper/live paths.

Phase W.1 — extract the entry confirmation gate (previously inline in
backtest/engine.py) so the exact same logic is reachable from paper_trading
ExecutionEngine. The gate stays pure: it takes (playbook_def, setup, candles_1m)
and returns a verdict. Instrumentation (debug_counts, reject-reason counters,
logger) remains in the caller.
"""

from dataclasses import dataclass
from typing import Optional, Sequence, Any


GATE_REASON_NO_CANDLES = "no_candles"
GATE_REASON_NO_COMMIT = "no_commit"


@dataclass
class GateResult:
    passed: bool
    reason: Optional[str] = None
    close_now: Optional[float] = None
    close_prev: Optional[float] = None
    buffer_abs: Optional[float] = None


def check_entry_confirmation(
    playbook_def: Any,
    setup: Any,
    candles_1m: Optional[Sequence[Any]],
) -> GateResult:
    """Entry confirmation gate.

    Require the most-recent 1m bar's close to have moved in the trade direction
    beyond the prior 1m bar's close by `entry_buffer_bps`. If the playbook does
    not enable `require_close_above_trigger`, the gate is a no-op pass.

    Returns a GateResult; the caller is responsible for incrementing stats and
    logging. This function never raises on missing attributes — it fails closed
    (reject) only when the playbook enables the gate AND the data is missing
    or the bar has not committed.
    """
    if not getattr(playbook_def, "require_close_above_trigger", False):
        return GateResult(passed=True)

    if not candles_1m or len(candles_1m) < 2:
        return GateResult(passed=False, reason=GATE_REASON_NO_CANDLES)

    bps = float(getattr(playbook_def, "entry_buffer_bps", 2.0))
    buffer_abs = float(setup.entry_price) * (bps / 10000.0)
    close_now = float(candles_1m[-1].close)
    close_prev = float(candles_1m[-2].close)

    direction = (getattr(setup, "direction", "") or "").upper()
    if direction == "LONG":
        committed = close_now > (close_prev + buffer_abs)
    elif direction == "SHORT":
        committed = close_now < (close_prev - buffer_abs)
    else:
        committed = False

    if not committed:
        return GateResult(
            passed=False,
            reason=GATE_REASON_NO_COMMIT,
            close_now=close_now,
            close_prev=close_prev,
            buffer_abs=buffer_abs,
        )

    return GateResult(
        passed=True,
        close_now=close_now,
        close_prev=close_prev,
        buffer_abs=buffer_abs,
    )
