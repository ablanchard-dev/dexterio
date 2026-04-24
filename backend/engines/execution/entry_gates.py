"""Shared entry gates callable from both backtest and paper/live paths.

Phase W.1 — extract the entry confirmation gate (previously inline in
backtest/engine.py) so the exact same logic is reachable from paper_trading
ExecutionEngine. The gate stays pure: it takes (playbook_def, setup, candles_1m)
and returns a verdict. Instrumentation (debug_counts, reject-reason counters,
logger) remains in the caller.

§0.B.5 extension (v4 Knowledge-Audit 2026-04-24) : macro kill zone overlay
gate. Source MASTER ligne 16028-16045 + TRUE `L4xz2o23aPQ` (TJR Time Theory) :
  - NY macro AM : 09:50-10:10 ET (post-manipulation entry window)
  - NY macro PM : 13:50-14:10 ET
  - Strict manip gate (optional) : 09:30-09:50 manipulation window → block
    entries ; 09:50-10:10 entry window → allow ; after 10:30 → block.
"""

from dataclasses import dataclass
from datetime import datetime, time
from typing import Optional, Sequence, Any
from zoneinfo import ZoneInfo


GATE_REASON_NO_CANDLES = "no_candles"
GATE_REASON_NO_COMMIT = "no_commit"

# §0.B.5 kill zone rejection reasons.
GATE_REASON_OUTSIDE_MACRO_WINDOW = "outside_macro_window"
GATE_REASON_MANIPULATION_WINDOW = "manipulation_window"
GATE_REASON_POST_CUTOFF = "post_cutoff"

_ET = ZoneInfo("America/New_York")

# Macro window boundaries in ET.
_MACRO_AM_START = time(9, 50)
_MACRO_AM_END = time(10, 10)
_MACRO_PM_START = time(13, 50)
_MACRO_PM_END = time(14, 10)

# Strict manipulation gate boundaries (alternative mode).
_MANIP_START = time(9, 30)
_MANIP_END = time(9, 50)
_CUTOFF = time(10, 30)


def _time_in_window(t: time, start: time, end: time) -> bool:
    """Closed-start, closed-end window membership (start <= t <= end)."""
    return start <= t <= end


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


def check_macro_kill_zone(
    ts: datetime,
    *,
    macro_am: bool = True,
    macro_pm: bool = True,
    strict_manip_gate: bool = False,
) -> GateResult:
    """§0.B.5 macro kill zone gate.

    Given a bar timestamp, return GateResult indicating whether entries are
    allowed. Timestamps are converted to ET for window membership.

    Windows (closed intervals, inclusive both sides) :
        - macro AM : 09:50 ET to 10:10 ET (default True)
        - macro PM : 13:50 ET to 14:10 ET (default True)

    Behaviour :
        - Default (strict_manip_gate=False) : pass iff ts in any enabled macro
          window. Outside all windows → reject `outside_macro_window`.
        - strict_manip_gate=True : additionally reject entries during the NY
          manipulation window 09:30-09:50 ET with reason `manipulation_window`,
          and reject entries after 10:30 ET cut-off with `post_cutoff` (PM is
          not affected by the strict manipulation gate — it is AM-specific per
          TRUE `L4xz2o23aPQ`).

    If neither macro_am nor macro_pm is enabled, the gate is a no-op pass
    (caller has disabled the overlay entirely).
    """
    if not macro_am and not macro_pm:
        return GateResult(passed=True)

    ts_et = ts.astimezone(_ET) if ts.tzinfo else ts.replace(tzinfo=_ET)
    t_et = ts_et.time()

    if strict_manip_gate:
        # Reject the manipulation window explicitly.
        if _time_in_window(t_et, _MANIP_START, _MANIP_END) and t_et != _MANIP_END:
            # Strict gate: reject manipulation window *before* the macro AM
            # starts. 09:50 exact belongs to macro AM (start boundary).
            return GateResult(passed=False, reason=GATE_REASON_MANIPULATION_WINDOW)
        # Post-cutoff only applies pre-PM (i.e. between 10:30 and PM start).
        if t_et > _CUTOFF and t_et < _MACRO_PM_START:
            return GateResult(passed=False, reason=GATE_REASON_POST_CUTOFF)

    in_am = macro_am and _time_in_window(t_et, _MACRO_AM_START, _MACRO_AM_END)
    in_pm = macro_pm and _time_in_window(t_et, _MACRO_PM_START, _MACRO_PM_END)

    if in_am or in_pm:
        return GateResult(passed=True)

    return GateResult(passed=False, reason=GATE_REASON_OUTSIDE_MACRO_WINDOW)
