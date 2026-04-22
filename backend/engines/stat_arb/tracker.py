"""PairSpreadTracker — stat arb state machine (Sprint 3, phase D2).

Template borrowed from Aplus01Tracker: per-pair state, trading-day reset,
timeouts, trace for journal. Logic mirrors dossier piece C:

    IDLE
      → (|z_t| >= entry_z AND cointegration pass)
    ARMED_LONG  (z_t <= -entry_z, buy spread: +y/-x)
    ARMED_SHORT (z_t >=  entry_z, sell spread: -y/+x)
      → next bar 5m emits setup
    IN_TRADE (managed by ExecutionEngine)
      → |z_t| <= exit_z : TP
      → |z_t| >= blowout_z : SL
      → bars_in_trade >= time_stop_bars : TIME_STOP
    LOCKOUT (N bars after exit to avoid ping-pong)

This tracker is pure logic. It does not ingest prices directly; the caller
feeds (ts, z_t, is_cointegrated, beta_t) per 5m bar and receives either a
setup dict or None.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

ET = ZoneInfo("America/New_York")

STATE_IDLE = "IDLE"
STATE_ARMED_LONG = "ARMED_LONG"
STATE_ARMED_SHORT = "ARMED_SHORT"
STATE_LOCKOUT = "LOCKOUT"


@dataclass
class _PairState:
    state: str = STATE_IDLE
    armed_at_ts: Optional[datetime] = None
    armed_z: Optional[float] = None
    armed_beta: Optional[float] = None
    lockout_bars_remaining: int = 0
    trading_date: Optional[date] = None
    trace: List[tuple] = field(default_factory=list)

    def reset_to_idle(self) -> None:
        self.state = STATE_IDLE
        self.armed_at_ts = None
        self.armed_z = None
        self.armed_beta = None
        # lockout_bars_remaining preserved across this reset

    def log(self, state: str, ts: datetime, detail: Any = None) -> None:
        self.trace.append((state, ts, detail))


def _to_et(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(ET)


def _trading_date_for(ts: datetime) -> date:
    """18:00 ET rollover, aligned with SessionRangeTracker convention."""
    et = _to_et(ts)
    if et.time() >= time(18, 0):
        return (et + timedelta(days=1)).date()
    return et.date()


class PairSpreadTracker:
    """Per-pair state machine. One tracker per (y_symbol, x_symbol) pair."""

    def __init__(
        self,
        *,
        entry_z: float = 2.0,
        exit_z: float = 0.5,
        blowout_z: float = 3.0,
        lockout_bars: int = 6,
        require_cointegration: bool = True,
    ) -> None:
        if entry_z <= exit_z:
            raise ValueError("entry_z must be > exit_z")
        if blowout_z <= entry_z:
            raise ValueError("blowout_z must be > entry_z")
        self.entry_z = float(entry_z)
        self.exit_z = float(exit_z)
        self.blowout_z = float(blowout_z)
        self.lockout_bars = int(lockout_bars)
        self.require_cointegration = bool(require_cointegration)
        self._state = _PairState()

    # -- inspection ---------------------------------------------------------

    @property
    def state(self) -> str:
        return self._state.state

    @property
    def trace(self) -> List[tuple]:
        return list(self._state.trace)

    # -- main entry point ---------------------------------------------------

    def on_5m_close(
        self,
        *,
        ts: datetime,
        z: float,
        beta: float,
        is_cointegrated: bool,
    ) -> Optional[Dict[str, Any]]:
        """Feed a 5m bar close. Returns a setup dict when transitioning
        IDLE → ARMED_*, else None.
        """
        st = self._state

        # Trading-day reset (18:00 ET rollover).
        td = _trading_date_for(ts)
        if st.trading_date is None:
            st.trading_date = td
        elif td != st.trading_date:
            st.reset_to_idle()
            st.lockout_bars_remaining = 0
            st.trading_date = td
            st.log("RESET_TRADING_DAY", ts, None)

        # Lockout: decrement and stay IDLE.
        if st.lockout_bars_remaining > 0:
            st.lockout_bars_remaining -= 1
            return None

        # From ARMED state: external ExecutionEngine owns the lifecycle.
        # We re-enter IDLE only via notify_trade_closed().
        if st.state in (STATE_ARMED_LONG, STATE_ARMED_SHORT):
            return None

        # IDLE: check entry conditions.
        if self.require_cointegration and not is_cointegrated:
            return None
        if z is None or beta is None:
            return None

        import math

        if math.isnan(z) or math.isnan(beta):
            return None

        if z <= -self.entry_z:
            st.state = STATE_ARMED_LONG
            direction = "long"
        elif z >= self.entry_z:
            st.state = STATE_ARMED_SHORT
            direction = "short"
        else:
            return None

        st.armed_at_ts = ts
        st.armed_z = float(z)
        st.armed_beta = float(beta)
        st.log(st.state, ts, {"z": float(z), "beta": float(beta)})

        return {
            "direction": direction,
            "armed_at_ts": ts,
            "armed_z": float(z),
            "armed_beta": float(beta),
            "entry_z_threshold": self.entry_z,
            "exit_z_threshold": self.exit_z,
            "blowout_z_threshold": self.blowout_z,
            "state_machine_trace": list(st.trace),
        }

    # -- lifecycle hook from ExecutionEngine --------------------------------

    def notify_trade_closed(self, ts: datetime, reason: str) -> None:
        """Called when the pair trade closes (TP/SL/TIME_STOP).

        Resets to IDLE and sets lockout to avoid immediate re-entry.
        """
        st = self._state
        st.log("TRADE_CLOSED", ts, reason)
        st.reset_to_idle()
        st.lockout_bars_remaining = self.lockout_bars
