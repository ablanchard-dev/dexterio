"""Equilibrium zone most-recent swing — §0.B.4 brique canon.

Source TRUE `wzq2AMsoJKY` ("THE Equilibrium Video") : EQ = 50% between the
**most recent** swing high and swing low. TJR insists (3 min screaming) on
the word "most recent" — not the extremes over a lookback window. The zone is
redrawn on each new HH/LL detected; the old zone is retired.

Déprécie le legacy [backend/engines/patterns/equilibrium.py] qui utilise
`max(window)` / `min(window)` sur lookback 20 bars — ça donne les extrêmes
absolus, pas le swing strict. Phase D.2 audit l'avait flaggé comme FANTASY
partiel (axe A5 MISSING partout per 04_CODE_AUDIT).

The new equilibrium_zone semantics :
  - Consume a list of Pivots (from directional_change k3 typically).
  - Track the last high and last low independently.
  - EQ = (last_high.price + last_low.price) / 2.
  - The zone becomes active the moment both a high and a low have been
    observed (never before — no zone without 1 of each).
  - The zone is "tapped" when a bar's range comes within `tolerance_atr × atr`
    of the EQ level (closed-interval overlap with the ±tolerance band).
  - Emitting a new pivot (HH/LL/LH/HL) refreshes the EQ if it changes the
    relevant extremum ; stale zones are not kept.

Contract :
    EquilibriumZone : dataclass frozen snapshot (level, swing_H/L ts, active,
                      last_tap_ts)
    compute_equilibrium_zone(pivots) -> EquilibriumZone | None
    bar_taps_equilibrium(zone, bar_high, bar_low, atr, tolerance_atr) -> bool

No state machine here (unlike §0.B.7 which is stateful for pool tracking).
Pure function — callers pass the latest pivots each bar; computed result is
point-in-time.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Sequence

from engines.features.pivot import Pivot


@dataclass(frozen=True)
class EquilibriumZone:
    """Frozen snapshot of the EQ derived from the most recent swing extrema."""

    level: float
    last_swing_H_price: float
    last_swing_L_price: float
    last_swing_H_ts: datetime
    last_swing_L_ts: datetime
    active: bool  # True iff we have at least 1 high + 1 low pivot
    last_tap_ts: Optional[datetime] = None  # set by caller via bar_taps_equilibrium


def compute_equilibrium_zone(
    pivots: Sequence[Pivot],
    *,
    last_tap_ts: Optional[datetime] = None,
) -> Optional[EquilibriumZone]:
    """Compute the EQ from the most-recent swing high and swing low in `pivots`.

    Returns None if pivots lack at least one high and one low.
    `pivots` must be chronological (ascending timestamp).
    `last_tap_ts` : caller-supplied (the zone is immutable; tap tracking is
    maintained externally by threading the latest tap ts into a fresh call
    each bar).
    """
    if not pivots:
        return None
    last_high: Optional[Pivot] = None
    last_low: Optional[Pivot] = None
    for p in reversed(pivots):
        if p.type == "high" and last_high is None:
            last_high = p
        elif p.type == "low" and last_low is None:
            last_low = p
        if last_high is not None and last_low is not None:
            break
    if last_high is None or last_low is None:
        return None
    level = (last_high.price + last_low.price) / 2.0
    return EquilibriumZone(
        level=level,
        last_swing_H_price=last_high.price,
        last_swing_L_price=last_low.price,
        last_swing_H_ts=last_high.timestamp,
        last_swing_L_ts=last_low.timestamp,
        active=True,
        last_tap_ts=last_tap_ts,
    )


def bar_taps_equilibrium(
    zone: EquilibriumZone,
    bar_high: float,
    bar_low: float,
    atr: float,
    tolerance_atr: float = 0.25,
) -> bool:
    """True if the bar's range touches the EQ level within ±(tolerance_atr×atr).

    Edge-touch counts (closed interval). ATR ≤ 0 or tolerance ≤ 0 falls back
    to exact-level overlap (bar contains zone.level).
    """
    if not zone.active:
        return False
    if atr <= 0.0 or tolerance_atr <= 0.0:
        return bar_low <= zone.level <= bar_high
    half_band = atr * tolerance_atr
    band_lo = zone.level - half_band
    band_hi = zone.level + half_band
    return bar_low <= band_hi and bar_high >= band_lo
