"""Aplus_01 Family A state machine tracker — first faithful MASTER instantiation.

Per dossier `backend/knowledge/playbooks/aplus_01_full_v1/dossier.md`,
implements the sequential cascade:

    IDLE
      → (sweep 5m close)
    ARMED_AFTER_SWEEP        (timeout: sweep_timeout 5m bars)
      → (BOS 5m in counter-sweep direction)
    BOS_CONFIRMED            (timeout: bos_timeout 5m bars)
      → (5m bar touches FVG ∪ breaker ∪ OB in armed direction)
    CONFLUENCE_TOUCHED       (timeout: confirm_timeout 1m bars)
      → (1m pressure confirm in armed direction)
    EMIT_SETUP

State is per-symbol so SPY and QQQ run independently. Trading-date reset
mirrors `SessionRangeTracker` (resets at 18:00 ET, NY trading day boundary)
so a stale state from yesterday cannot trigger today.

The tracker is **pure logic** — it does not detect sweeps/BOS/zones itself.
The caller (engine wire-up) extracts those from existing detectors and feeds
them through `on_5m_close()`. The 1m confirm uses `pressure_confirm` and the
zone touch uses `confluence_zone` — both pure helpers under
`engines.features`.

Returns from `on_1m_bar()`: a setup dict or None.
    {
        "direction": "bullish" | "bearish",
        "entry_price": float,        # 1m close at confirm time
        "sl_anchor_price": float,    # extremum of the sweep bar (structural SL)
        "armed_at_ts": datetime,     # UTC timestamp of the sweep bar
        "bos_at_ts": datetime,
        "touched_at_ts": datetime,
        "confirmed_at_ts": datetime,
        "touched_zone_type": str,    # "fvg" | "breaker" | "order_block"
        "touched_zone_id": str | None,
        "state_machine_trace": list, # ordered (state, ts, detail) tuples for journal
    }
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence
from zoneinfo import ZoneInfo

from engines.features.confluence_zone import Zone, bar_touches_any_zone
from engines.features.pressure_confirm import has_1m_pressure

logger = logging.getLogger(__name__)

ET = ZoneInfo("America/New_York")

STATE_IDLE = "IDLE"
STATE_ARMED = "ARMED_AFTER_SWEEP"
STATE_BOS = "BOS_CONFIRMED"
STATE_TOUCHED = "CONFLUENCE_TOUCHED"


@dataclass
class _SymbolState:
    state: str = STATE_IDLE
    armed_direction: Optional[str] = None        # "bullish" | "bearish"
    sweep_ts: Optional[datetime] = None
    sweep_extreme_price: Optional[float] = None  # SL anchor candidate
    bos_ts: Optional[datetime] = None
    touched_ts: Optional[datetime] = None
    touched_zone_type: Optional[str] = None
    touched_zone_id: Optional[str] = None
    bars_5m_in_state: int = 0
    bars_1m_since_touch: int = 0
    trading_date: Optional[date] = None
    trace: List[tuple] = field(default_factory=list)

    def reset_to_idle(self) -> None:
        self.state = STATE_IDLE
        self.armed_direction = None
        self.sweep_ts = None
        self.sweep_extreme_price = None
        self.bos_ts = None
        self.touched_ts = None
        self.touched_zone_type = None
        self.touched_zone_id = None
        self.bars_5m_in_state = 0
        self.bars_1m_since_touch = 0
        self.trace = []


def _to_utc(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts


def _trading_date_for(ts_utc: datetime) -> date:
    """NY trading date (rolls at 18:00 ET — same convention as SessionRangeTracker)."""
    ts_et = ts_utc.astimezone(ET)
    if ts_et.time() >= time(18, 0):
        return ts_et.date() + timedelta(days=1)
    return ts_et.date()


class Aplus01Tracker:
    """Per-symbol stateful sequential detector for the Aplus_01 cascade."""

    def __init__(
        self,
        sweep_timeout: int = 20,
        bos_timeout: int = 6,
        confirm_timeout: int = 12,
        pressure_window: int = 12,
        pressure_bos_lookback: int = 5,
    ):
        self.sweep_timeout = sweep_timeout
        self.bos_timeout = bos_timeout
        self.confirm_timeout = confirm_timeout
        self.pressure_window = pressure_window
        self.pressure_bos_lookback = pressure_bos_lookback
        self._states: Dict[str, _SymbolState] = {}

    def get_state(self, symbol: str) -> str:
        return self._states.get(symbol, _SymbolState()).state

    def reset(self) -> None:
        self._states.clear()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def on_5m_close(
        self,
        symbol: str,
        ts_utc: datetime,
        *,
        sweep: Optional[Dict[str, Any]] = None,
        bos: Optional[Dict[str, Any]] = None,
        zones: Optional[Sequence[Zone]] = None,
        bar_high: Optional[float] = None,
        bar_low: Optional[float] = None,
    ) -> None:
        """Advance state on a 5m bar close.

        sweep: {"direction": "bullish"|"bearish", "extreme_price": float}
               where direction is the SWEEP direction (high-sweep = "bullish",
               low-sweep = "bearish"). Tracker computes counter-direction.
        bos:   {"direction": "bullish"|"bearish"}.
        zones: list[Zone] currently armed (FVG/breaker/OB intervals).
        bar_high/bar_low: required for zone-touch test in BOS_CONFIRMED state.
        """
        ts_utc = _to_utc(ts_utc)
        st = self._get_or_init(symbol, ts_utc)

        # Daily reset
        td = _trading_date_for(ts_utc)
        if st.trading_date is None:
            st.trading_date = td
        elif td != st.trading_date:
            st.reset_to_idle()
            st.trading_date = td

        # Tick the in-state 5m counter and check timeouts BEFORE transitions
        if st.state != STATE_IDLE:
            st.bars_5m_in_state += 1
            if self._timed_out_5m(st):
                self._record(st, "TIMEOUT_5M", ts_utc, st.state)
                st.reset_to_idle()

        # IDLE → ARMED on sweep
        if st.state == STATE_IDLE and sweep is not None:
            sweep_dir = sweep.get("direction")
            if sweep_dir in ("bullish", "bearish"):
                st.state = STATE_ARMED
                st.armed_direction = "bearish" if sweep_dir == "bullish" else "bullish"
                st.sweep_ts = ts_utc
                st.sweep_extreme_price = sweep.get("extreme_price")
                st.bars_5m_in_state = 0
                self._record(st, STATE_ARMED, ts_utc, {"sweep_dir": sweep_dir})
                return

        # ARMED → BOS_CONFIRMED on counter-direction BOS
        if st.state == STATE_ARMED and bos is not None:
            if bos.get("direction") == st.armed_direction:
                st.state = STATE_BOS
                st.bos_ts = ts_utc
                st.bars_5m_in_state = 0
                self._record(st, STATE_BOS, ts_utc, {"bos_dir": bos["direction"]})
                return

        # BOS_CONFIRMED → CONFLUENCE_TOUCHED on zone touch in armed direction
        if (
            st.state == STATE_BOS
            and zones
            and bar_high is not None
            and bar_low is not None
        ):
            touched, ztype, zid = bar_touches_any_zone(bar_low, bar_high, zones)
            if touched:
                st.state = STATE_TOUCHED
                st.touched_ts = ts_utc
                st.touched_zone_type = ztype
                st.touched_zone_id = zid
                st.bars_5m_in_state = 0
                st.bars_1m_since_touch = 0
                self._record(
                    st,
                    STATE_TOUCHED,
                    ts_utc,
                    {"zone_type": ztype, "zone_id": zid},
                )
                return

    def on_1m_bar(
        self,
        symbol: str,
        ts_utc: datetime,
        bar_1m: Any,
        recent_1m_bars: Sequence[Any],
    ) -> Optional[Dict[str, Any]]:
        """Check 1m pressure confirm. Returns emit dict or None.

        Once an emit fires, tracker resets to IDLE (single-shot per cascade).
        """
        ts_utc = _to_utc(ts_utc)
        st = self._states.get(symbol)
        if st is None or st.state != STATE_TOUCHED:
            return None

        st.bars_1m_since_touch += 1
        if st.bars_1m_since_touch > self.confirm_timeout:
            self._record(st, "TIMEOUT_1M_CONFIRM", ts_utc, None)
            st.reset_to_idle()
            return None

        if not has_1m_pressure(
            recent_1m_bars,
            st.armed_direction,
            window=self.pressure_window,
            bos_lookback=self.pressure_bos_lookback,
        ):
            return None

        emit = {
            "direction": st.armed_direction,
            "entry_price": float(bar_1m.close),
            "sl_anchor_price": st.sweep_extreme_price,
            "armed_at_ts": st.sweep_ts,
            "bos_at_ts": st.bos_ts,
            "touched_at_ts": st.touched_ts,
            "confirmed_at_ts": ts_utc,
            "touched_zone_type": st.touched_zone_type,
            "touched_zone_id": st.touched_zone_id,
            "state_machine_trace": list(st.trace) + [("EMIT", ts_utc, None)],
        }
        st.reset_to_idle()
        return emit

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _get_or_init(self, symbol: str, ts_utc: datetime) -> _SymbolState:
        st = self._states.get(symbol)
        if st is None:
            st = _SymbolState(trading_date=_trading_date_for(ts_utc))
            self._states[symbol] = st
        return st

    def _timed_out_5m(self, st: _SymbolState) -> bool:
        if st.state == STATE_ARMED:
            return st.bars_5m_in_state > self.sweep_timeout
        if st.state == STATE_BOS:
            return st.bars_5m_in_state > self.bos_timeout
        # STATE_TOUCHED uses the 1m counter (handled in on_1m_bar)
        return False

    def _record(
        self, st: _SymbolState, label: str, ts_utc: datetime, detail: Any
    ) -> None:
        st.trace.append((label, ts_utc, detail))
