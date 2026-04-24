"""SMT cross-index state machine tracker — §0.5bis entrée #1 support.

Orchestrator per-symbol-pair (SPY/QQQ default) coordinating :
    §0.B.7 PoolFreshnessTracker → pool sweep events
    §0.B.2 detect_smt_divergence → SMTSignal emission
    §0.B.3 compute_htf_bias     → bias alignment gate
    §0.B.5 check_macro_kill_zone → temporal gate
    §0.B.6 classify_session_profile → regime filter
    §0.B.8 check_pre_sweep_gate → IFVG-style pre-sweep check

5-state machine (mirrors Aplus01Tracker pattern) :
    IDLE
      ↓ (pool HTF 4H/1H fresh sweeped on SPY or QQQ)
    POOL_SWEEPED (timeout: 30 bars 5m = 150 min)
      ↓ (≥ 2 k3 pivots post-sweep on both indices, 1 high + 1 low each)
    STRUCTURE_OBSERVABLE (timeout: 20 bars 5m = 100 min)
      ↓ (detect_smt_divergence → SMTSignal not None)
    SMT_SIGNAL_EMITTED (timeout: 6 bars 5m = 30 min)
      ↓ (htf_bias aligned, macro kill zone pass, daily profile allowed,
          pre_sweep_gate pass)
    EMIT_SETUP (terminal — setup delivered, reset to IDLE after setup_engine consumes)

The tracker does not execute trades. It emits a `TrackerOutput` each bar with
the current state and, when EMIT_SETUP, a fully-qualified `SMTSetupCandidate`
that setup_engine_v2 consumes (entry_price, direction, tp_logic_params,
sl reference pivots, etc.).

Per-day reset at 18:00 ET rollover (compute_trading_date from §0.B.7).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Literal, Optional

from engines.features.pool_freshness_tracker import compute_trading_date
from engines.patterns.smt_htf import SMTSignal


class SMTState(str, Enum):
    IDLE = "IDLE"
    POOL_SWEEPED = "POOL_SWEEPED"
    STRUCTURE_OBSERVABLE = "STRUCTURE_OBSERVABLE"
    SMT_SIGNAL_EMITTED = "SMT_SIGNAL_EMITTED"
    EMIT_SETUP = "EMIT_SETUP"


@dataclass(frozen=True)
class SMTSetupCandidate:
    """Fully-qualified setup ready for setup_engine_v2 consumption."""

    symbol: str  # lagging symbol (the one we trade)
    direction: Literal["LONG", "SHORT"]
    entry_reference_price: float
    smt_completion_price: float
    leading_symbol: str
    divergence_type: Literal["bull", "bear"]
    pool_sweep_tf: str
    pool_sweep_ts: datetime
    signal_ts: datetime


@dataclass(frozen=True)
class TrackerOutput:
    """Per-bar tracker output."""

    state: SMTState
    setup: Optional[SMTSetupCandidate] = None
    reason: Optional[str] = None  # debug trace (e.g. "timeout_POOL_SWEEPED")


@dataclass
class _StateData:
    """Internal mutable state — dataclass (not frozen) for in-place updates."""

    state: SMTState = SMTState.IDLE
    state_entered_at: Optional[datetime] = None
    pool_sweep_ts: Optional[datetime] = None
    pool_sweep_tf: Optional[str] = None
    pool_sweep_symbol: Optional[str] = None
    last_signal: Optional[SMTSignal] = None
    trading_date: Optional[Any] = None  # date, compute_trading_date


# Default timeout policy (in minutes).
_TIMEOUTS_MIN = {
    SMTState.POOL_SWEEPED: 150,
    SMTState.STRUCTURE_OBSERVABLE: 100,
    SMTState.SMT_SIGNAL_EMITTED: 30,
}


class SMTCrossIndexTracker:
    """5-state machine per symbol-pair.

    Typical usage :
        tracker = SMTCrossIndexTracker(pair=("SPY", "QQQ"))
        for bar_ts in timeline:
            # 1. Feed pool sweep events (if any on this bar)
            if swept_pools:
                tracker.on_pool_sweeps(swept_pools, symbol, tf, bar_ts)
            # 2. Feed bar tick (handles timeouts + rollovers)
            tracker.on_bar_tick(bar_ts)
            # 3. Attempt signal detection
            signal = detect_smt_divergence(spy_inputs, qqq_inputs, bar_ts,
                                           sweep_ts=tracker.pool_sweep_ts)
            if signal is not None:
                tracker.on_signal(signal, bar_ts)
            # 4. Attempt setup emission (all gates must pass)
            out = tracker.try_emit_setup(
                bar_ts=bar_ts,
                htf_bias_aligned=bias_aligned,
                macro_kill_zone_pass=macro_pass,
                daily_profile_allowed=profile_ok,
                pre_sweep_gate_pass=presweep_ok,
            )
            if out.setup:
                submit_to_setup_engine(out.setup)
                tracker.reset_after_emit()
    """

    def __init__(
        self,
        pair: tuple[str, str] = ("SPY", "QQQ"),
        timeouts_min: Optional[dict[SMTState, int]] = None,
    ) -> None:
        self._pair = pair
        self._timeouts_min = timeouts_min if timeouts_min is not None else dict(_TIMEOUTS_MIN)
        self._data = _StateData()

    @property
    def state(self) -> SMTState:
        return self._data.state

    @property
    def pair(self) -> tuple[str, str]:
        return self._pair

    @property
    def pool_sweep_ts(self) -> Optional[datetime]:
        return self._data.pool_sweep_ts

    def on_pool_sweeps(
        self,
        *,
        swept_pool_ids: list[str],
        symbol: str,
        tf: str,
        bar_ts: datetime,
    ) -> None:
        """Consume a batch of swept pool ids from PoolFreshnessTracker.update().

        Only HTF pools (4h or 1h) arm the tracker. Lower-TF sweeps are ignored
        (they do not meet the canon TRUE pKIo-aVic-c freshness hierarchy for
        dual-asset SMT entries).
        """
        if self._data.state != SMTState.IDLE:
            # Already armed — ignore additional sweeps (state machine linear).
            return
        if tf not in ("4h", "1h"):
            return
        if symbol not in self._pair:
            return
        if not swept_pool_ids:
            return
        self._data.state = SMTState.POOL_SWEEPED
        self._data.state_entered_at = bar_ts
        self._data.pool_sweep_ts = bar_ts
        self._data.pool_sweep_tf = tf
        self._data.pool_sweep_symbol = symbol

    def advance_to_structure_observable(self, bar_ts: datetime) -> None:
        """Caller signals that both indices now have sufficient post-sweep k3 structure.

        Moves POOL_SWEEPED → STRUCTURE_OBSERVABLE. No-op if not in POOL_SWEEPED.
        """
        if self._data.state != SMTState.POOL_SWEEPED:
            return
        self._data.state = SMTState.STRUCTURE_OBSERVABLE
        self._data.state_entered_at = bar_ts

    def on_signal(self, signal: SMTSignal, bar_ts: datetime) -> None:
        """Consume a freshly-detected SMTSignal.

        Must be called only when state == STRUCTURE_OBSERVABLE. No-op otherwise.
        """
        if self._data.state != SMTState.STRUCTURE_OBSERVABLE:
            return
        # Defensive : signal must be for our pair.
        pair_set = set(self._pair)
        if {signal.leading_symbol, signal.lagging_symbol} != pair_set:
            return
        self._data.last_signal = signal
        self._data.state = SMTState.SMT_SIGNAL_EMITTED
        self._data.state_entered_at = bar_ts

    def try_emit_setup(
        self,
        *,
        bar_ts: datetime,
        htf_bias_aligned: bool,
        macro_kill_zone_pass: bool,
        daily_profile_allowed: bool,
        pre_sweep_gate_pass: bool,
    ) -> TrackerOutput:
        """Attempt to move SMT_SIGNAL_EMITTED → EMIT_SETUP.

        All four gates must pass in the same bar for the setup to emit. If any
        gate fails, the tracker stays in SMT_SIGNAL_EMITTED until timeout OR a
        subsequent bar where all gates align.
        """
        if self._data.state != SMTState.SMT_SIGNAL_EMITTED or self._data.last_signal is None:
            return TrackerOutput(state=self._data.state)
        if not (
            htf_bias_aligned and macro_kill_zone_pass and
            daily_profile_allowed and pre_sweep_gate_pass
        ):
            return TrackerOutput(state=self._data.state, reason="gates_pending")

        sig = self._data.last_signal
        assert self._data.pool_sweep_ts is not None
        assert self._data.pool_sweep_tf is not None
        candidate = SMTSetupCandidate(
            symbol=sig.lagging_symbol,
            direction=sig.direction,
            entry_reference_price=sig.lagging_entry_reference,
            smt_completion_price=sig.smt_completion_target,
            leading_symbol=sig.leading_symbol,
            divergence_type=sig.divergence_type,
            pool_sweep_tf=self._data.pool_sweep_tf,
            pool_sweep_ts=self._data.pool_sweep_ts,
            signal_ts=sig.detected_ts,
        )
        self._data.state = SMTState.EMIT_SETUP
        self._data.state_entered_at = bar_ts
        return TrackerOutput(state=SMTState.EMIT_SETUP, setup=candidate)

    def on_bar_tick(self, bar_ts: datetime) -> TrackerOutput:
        """Feed every bar. Handles trading-day rollover + state timeouts.

        Returns a TrackerOutput with the current state ; if a timeout or
        rollover occurred, the reason field is set.
        """
        # Trading-day rollover : reset tracker entirely.
        td = compute_trading_date(bar_ts)
        if self._data.trading_date is None:
            self._data.trading_date = td
        elif td != self._data.trading_date:
            self._data = _StateData(state=SMTState.IDLE, trading_date=td)
            return TrackerOutput(state=SMTState.IDLE, reason="trading_day_rollover")

        # Timeout check for timed states.
        if self._data.state in self._timeouts_min and self._data.state_entered_at is not None:
            max_min = self._timeouts_min[self._data.state]
            if (bar_ts - self._data.state_entered_at) > timedelta(minutes=max_min):
                reason = f"timeout_{self._data.state.value}"
                self._data = _StateData(state=SMTState.IDLE, trading_date=td)
                return TrackerOutput(state=SMTState.IDLE, reason=reason)

        return TrackerOutput(state=self._data.state)

    def reset_after_emit(self) -> None:
        """Caller calls this after consuming an EMIT_SETUP candidate.

        Resets to IDLE preserving the trading_date (intraday retrigger ok).
        """
        td = self._data.trading_date
        self._data = _StateData(state=SMTState.IDLE, trading_date=td)
