"""Confluence zone touch detector — pure geometric helper (Aplus_01 brick).

A "zone" is a price interval (low, high) with a type tag (e.g. "fvg",
"breaker", "order_block") and an optional id. A "touch" occurs when a bar's
[low, high] range overlaps the zone's [low, high] range — inclusive on both
sides (touching the edge counts).

Designed to be reusable across playbooks: anything that needs "did the
current bar enter one of N pre-armed zones?" can call this. Pure function,
no state, no I/O. Cheap enough to call per-bar.

Contract:
    Zone = {"type": str, "low": float, "high": float, "id": str | None}
    bar_touches_any_zone(bar_low, bar_high, zones) -> (touched, type, id)

The first matching zone (in insertion order) wins. Caller decides whether
ties matter and how to break them.
"""
from __future__ import annotations

from typing import Iterable, Optional, Sequence, Tuple, TypedDict


class Zone(TypedDict, total=False):
    type: str        # "fvg" | "breaker" | "order_block" | ...
    low: float       # zone lower bound (inclusive)
    high: float      # zone upper bound (inclusive)
    id: Optional[str]  # opaque caller-side identifier


def _ranges_overlap(a_lo: float, a_hi: float, b_lo: float, b_hi: float) -> bool:
    """Closed-interval overlap. True iff [a_lo,a_hi] ∩ [b_lo,b_hi] ≠ ∅."""
    return a_lo <= b_hi and b_lo <= a_hi


def bar_touches_zone(
    bar_low: float, bar_high: float, zone_low: float, zone_high: float
) -> bool:
    """Does the bar [bar_low, bar_high] touch the zone [zone_low, zone_high]?

    Touch is closed-interval overlap (edge-touch counts).
    Caller is responsible for ensuring lo <= hi on both sides.
    """
    return _ranges_overlap(bar_low, bar_high, zone_low, zone_high)


def bar_touches_any_zone(
    bar_low: float,
    bar_high: float,
    zones: Sequence[Zone] | Iterable[Zone],
) -> Tuple[bool, Optional[str], Optional[str]]:
    """Find the first zone whose interval the bar touches.

    Returns (touched, zone_type, zone_id). On no match: (False, None, None).
    Iteration order matters — caller is expected to pre-sort zones if a
    specific priority is desired (e.g. FVG > breaker > OB).
    """
    for z in zones:
        z_lo = float(z["low"])
        z_hi = float(z["high"])
        if z_lo > z_hi:
            z_lo, z_hi = z_hi, z_lo
        if _ranges_overlap(bar_low, bar_high, z_lo, z_hi):
            return True, z.get("type"), z.get("id")
    return False, None, None
