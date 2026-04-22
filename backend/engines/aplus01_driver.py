"""Aplus_01 driver — bridges Aplus01Tracker to the existing engine pipeline.

Strategy: when the tracker emits, the driver returns a synthetic
`ICTPattern(pattern_type='aplus01_sequence')` carrying the cascade context.
This pattern joins the regular `ict_patterns` list passed to
`SetupEngineV2.generate_setups`, where:

  - `playbook_loader` matches it via `required_signals: ['APLUS01@1m']`
    (mapped through `type_map`),
  - `_determine_direction` reads its `direction` (added to `indicator_types`),
  - `_calculate_price_levels` uses its `price_level` (=sweep extreme) as the
    structural SL anchor, then resolves TP via the playbook's `tp_logic`.

This bypasses no risk-engine, journal, or fill-model layer — Aplus_01 setups
flow through the same plumbing as every other playbook.

Per-symbol state lives inside `Aplus01Tracker`. The driver itself is
stateless beyond holding the tracker reference.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

from engines.features.aplus01_tracker import Aplus01Tracker
from models.market_data import Candle
from models.setup import ICTPattern

logger = logging.getLogger(__name__)


def _zone_bounds(p: ICTPattern) -> Optional[tuple]:
    """Extract (low, high) from an ICTPattern's details, regardless of schema."""
    d = p.details or {}
    if "zone_low" in d and "zone_high" in d:
        return float(d["zone_low"]), float(d["zone_high"])
    if "bottom" in d and "top" in d:
        return float(d["bottom"]), float(d["top"])
    return None


def _sweep_payload(sweep_pat: ICTPattern) -> Optional[Dict[str, Any]]:
    """Convert a `liquidity_sweep` ICTPattern to tracker sweep dict.

    ICT engine's sweep `direction` = REACTION direction (bearish after a
    high-sweep, bullish after a low-sweep). Tracker expects `direction` =
    SWEEP direction (which side was swept). Invert.

    `price_level` on the sweep ICTPattern is the swept extreme — exactly the
    structural SL anchor we want to carry forward.
    """
    react_dir = (sweep_pat.direction or "").lower()
    if react_dir == "bearish":
        sweep_dir = "bullish"   # high was swept
    elif react_dir == "bullish":
        sweep_dir = "bearish"   # low was swept
    else:
        return None
    return {
        "direction": sweep_dir,
        "extreme_price": float(sweep_pat.price_level or 0.0),
    }


def _bos_payload(bos_pat: ICTPattern) -> Optional[Dict[str, Any]]:
    direction = (bos_pat.direction or "").lower()
    if direction not in ("bullish", "bearish"):
        return None
    return {"direction": direction}


def _collect_zones(det_5m: Dict[str, List[ICTPattern]]) -> List[Dict[str, Any]]:
    """Build a list of confluence zones from FVG ∪ breaker ∪ OB."""
    zones: List[Dict[str, Any]] = []
    for ztype in ("fvg", "breaker_block", "order_block"):
        for p in det_5m.get(ztype, []) or []:
            bounds = _zone_bounds(p)
            if bounds is None:
                continue
            lo, hi = bounds
            zones.append({
                "type": ztype,
                "low": lo,
                "high": hi,
                "id": getattr(p, "id", None),
                "direction": (p.direction or "").lower(),
            })
    return zones


class Aplus01Driver:
    """Driver coupling Aplus01Tracker to the engine bar-loop."""

    def __init__(
        self,
        sweep_timeout: int = 20,
        bos_timeout: int = 6,
        confirm_timeout: int = 12,
        pressure_window: int = 12,
        pressure_bos_lookback: int = 5,
        recent_1m_window: int = 20,
    ):
        self.tracker = Aplus01Tracker(
            sweep_timeout=sweep_timeout,
            bos_timeout=bos_timeout,
            confirm_timeout=confirm_timeout,
            pressure_window=pressure_window,
            pressure_bos_lookback=pressure_bos_lookback,
        )
        self.recent_1m_window = recent_1m_window
        self._emit_count: Dict[str, int] = {}

    # ------------------------------------------------------------------

    def on_5m_close(
        self,
        symbol: str,
        ts_utc: datetime,
        candles_5m: Sequence[Candle],
        det_5m: Dict[str, List[ICTPattern]],
    ) -> None:
        """Feed the tracker on a 5m close with the latest sweep/BOS/zones."""
        if not candles_5m:
            return
        last_5m = candles_5m[-1]

        sweep_pats = det_5m.get("liquidity_sweep") or []
        bos_pats = det_5m.get("bos") or []

        sweep_payload = _sweep_payload(sweep_pats[-1]) if sweep_pats else None
        bos_payload = _bos_payload(bos_pats[-1]) if bos_pats else None
        zones = _collect_zones(det_5m)

        self.tracker.on_5m_close(
            symbol,
            ts_utc,
            sweep=sweep_payload,
            bos=bos_payload,
            zones=zones,
            bar_high=float(last_5m.high),
            bar_low=float(last_5m.low),
        )

    def on_1m_bar(
        self,
        symbol: str,
        ts_utc: datetime,
        candles_1m: Sequence[Candle],
    ) -> Optional[ICTPattern]:
        """Tick the 1m confirm. Return a synthetic ICTPattern on emit, else None."""
        if not candles_1m:
            return None
        bar = candles_1m[-1]
        recent = candles_1m[-self.recent_1m_window:]
        emit = self.tracker.on_1m_bar(symbol, ts_utc, bar, recent)
        if not emit:
            return None

        self._emit_count[symbol] = self._emit_count.get(symbol, 0) + 1
        direction = emit["direction"]              # "bullish" | "bearish"
        sl_anchor = emit.get("sl_anchor_price")    # sweep extreme
        if sl_anchor is None or sl_anchor <= 0:
            logger.warning(
                "[APLUS01] %s emit at %s missing sl_anchor — dropping", symbol, ts_utc
            )
            return None

        synthetic = ICTPattern(
            symbol=symbol,
            timeframe="1m",
            pattern_type="aplus01_sequence",
            direction=direction,
            price_level=float(sl_anchor),  # used by setup_engine as structural SL anchor
            details={
                "armed_at_ts": (
                    emit["armed_at_ts"].isoformat() if emit.get("armed_at_ts") else None
                ),
                "bos_at_ts": (
                    emit["bos_at_ts"].isoformat() if emit.get("bos_at_ts") else None
                ),
                "touched_at_ts": (
                    emit["touched_at_ts"].isoformat() if emit.get("touched_at_ts") else None
                ),
                "confirmed_at_ts": (
                    emit["confirmed_at_ts"].isoformat()
                    if emit.get("confirmed_at_ts") else None
                ),
                "touched_zone_type": emit.get("touched_zone_type"),
                "touched_zone_id": emit.get("touched_zone_id"),
                "entry_price_at_confirm": emit.get("entry_price"),
                "state_machine_trace": [
                    (lbl, ts.isoformat() if hasattr(ts, "isoformat") else str(ts), det)
                    for (lbl, ts, det) in emit.get("state_machine_trace", [])
                ],
            },
            strength=1.0,        # dominate other directional ICT signals in _determine_direction
            confidence=0.95,
        )
        logger.info(
            "[APLUS01] %s emit %s at %s entry=%.4f sl_anchor=%.4f zone=%s",
            symbol,
            direction,
            ts_utc,
            float(emit.get("entry_price", 0.0)),
            float(sl_anchor),
            emit.get("touched_zone_type"),
        )
        return synthetic

    # ------------------------------------------------------------------

    def reset(self) -> None:
        self.tracker.reset()
        self._emit_count.clear()

    @property
    def emit_count(self) -> Dict[str, int]:
        return dict(self._emit_count)
