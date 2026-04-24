"""Stacked FVG rule + pre-sweep gate IFVG — §0.B.8 brique canon.

Source : TRUE `TEp3a-7GUds` (stacking rule : "last invalidates, not first") +
TRUE `BdBxXKGWVjk` (pre-sweep gate : IFVG entry requires HTF sweep dans fenêtre
pré-entry). Both were absent from Aplus_03 IFVG_Flip_5m versions v1/R.3/v2/α''
(4 ARCHIVED data points with IFVG signal isolé + fixed RR 2R).

Two independent helpers :

1. **group_fvg_stack** : partitions a sequence of same-direction FVGs into
   stacks. Two FVGs belong to the same stack iff they share direction AND no
   opposite-color bar sits strictly between their creation timestamps. Mixed-
   direction FVGs are impossible in the same stack by definition.

2. **invalidate_stacked_fvgs** : applies the canon rule "last invalidates,
   not first" — when a closing bar closes counter to the stack direction
   through the range of the **last** FVG, only that last FVG is invalidated.
   The earlier (deeper) FVGs in the stack survive and remain in play.

3. **check_pre_sweep_gate** : gate helper — True iff a sweep event occurred
   within the pre-entry window `[current_ts - max_window_minutes, current_ts]`.
   Canon TRUE : IFVG entry is only valid post-HTF-sweep (freshly generated
   liquidity).

Kept as a standalone module (not patched into ifvg.py / ict.py) to avoid
coupling legacy detector tests with the new rules. Callers opt-in explicitly.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, List, Literal, Optional, Sequence


FVGDirection = Literal["bullish", "bearish"]


@dataclass(frozen=True)
class FVGCandle:
    """A FVG candidate with its creation bar info.

    `direction` — "bullish" gap supports LONG (gap between prev_high and
    next_low in an upmove) ; "bearish" mirror.
    """

    id: str
    low: float
    high: float
    direction: FVGDirection
    created_ts: datetime
    invalidated: bool = False


def group_fvg_stack(
    fvgs: Sequence[FVGCandle],
    bars_between: Sequence[Any],
) -> List[List[FVGCandle]]:
    """Partition `fvgs` into stacks of same-direction consecutive FVGs.

    Two adjacent FVGs (in chronological order) form a stack iff :
      - they share `direction`, AND
      - no "opposite-color" bar exists strictly between their creation
        timestamps in `bars_between`.

    "Opposite-color" here means a bar whose close is on the side **opposite**
    to the FVG's direction : for a bullish FVG, an opposite bar has close <
    open (red); for a bearish FVG, close > open (green).

    `bars_between` : chronological sequence of bars with .open/.close/.timestamp
    attributes covering at least the FVG creation timespan.
    """
    if not fvgs:
        return []

    # Sort by created_ts (defensive — callers should pre-sort).
    fvgs_sorted = sorted(fvgs, key=lambda f: f.created_ts)

    stacks: List[List[FVGCandle]] = [[fvgs_sorted[0]]]
    for current in fvgs_sorted[1:]:
        prev = stacks[-1][-1]
        same_direction = current.direction == prev.direction
        opposite_bar_between = _has_opposite_color_bar(
            bars_between, prev.created_ts, current.created_ts, prev.direction
        )
        if same_direction and not opposite_bar_between:
            stacks[-1].append(current)
        else:
            stacks.append([current])
    return stacks


def _has_opposite_color_bar(
    bars: Sequence[Any],
    after_ts: datetime,
    before_ts: datetime,
    direction: FVGDirection,
) -> bool:
    """True if any bar strictly between (after_ts, before_ts) closes opposite.

    For bullish direction : opposite = red bar (close < open).
    For bearish direction : opposite = green bar (close > open).
    """
    for bar in bars:
        bar_ts = getattr(bar, "timestamp", None)
        if bar_ts is None:
            continue
        if bar_ts <= after_ts or bar_ts >= before_ts:
            continue
        b_open = float(getattr(bar, "open"))
        b_close = float(getattr(bar, "close"))
        if direction == "bullish" and b_close < b_open:
            return True
        if direction == "bearish" and b_close > b_open:
            return True
    return False


def invalidate_stacked_fvgs(
    stack: Sequence[FVGCandle],
    closing_bar_high: float,
    closing_bar_low: float,
    closing_bar_close: float,
) -> List[FVGCandle]:
    """Apply the canon rule : the closing bar invalidates **only the last**
    FVG of the stack, not the earlier ones.

    Rules :
      - Stack direction = direction of all FVGs in the stack (they agree by
        `group_fvg_stack` invariant).
      - The closing bar "invalidates" a FVG iff it closes counter-direction
        through the FVG range.
          bullish FVG : invalidated if closing_bar_close < FVG.low.
          bearish FVG : invalidated if closing_bar_close > FVG.high.
      - If the closing bar does invalidate the *last* FVG, return a new list
        where only the last is marked `invalidated=True` ; the earlier
        FVGs of the stack stay untouched.
      - If the closing bar does not invalidate the last FVG, the stack is
        returned unchanged.

    Returns a **new** list (inputs are frozen dataclasses — new instances).
    """
    if not stack:
        return []

    ordered = list(stack)
    last = ordered[-1]

    invalidates_last = False
    if last.direction == "bullish" and closing_bar_close < last.low:
        invalidates_last = True
    elif last.direction == "bearish" and closing_bar_close > last.high:
        invalidates_last = True

    if not invalidates_last:
        return ordered  # nothing changes

    # Only the last is flagged invalidated.
    updated_last = FVGCandle(
        id=last.id, low=last.low, high=last.high,
        direction=last.direction, created_ts=last.created_ts,
        invalidated=True,
    )
    return ordered[:-1] + [updated_last]


def check_pre_sweep_gate(
    *,
    sweep_event_ts: Optional[datetime],
    current_ts: datetime,
    max_window_minutes: int,
) -> bool:
    """True iff a sweep event occurred within (current_ts - window, current_ts].

    Canon TRUE `BdBxXKGWVjk` : IFVG entry is gated on a fresh pool sweep within
    the prior window — the sweep generates the liquidity that makes the flip
    meaningful. Without it, an IFVG is just a structural wiggle.

    Returns False when `sweep_event_ts is None` (no sweep → no entry) or when
    the sweep is too old (outside the window) or in the future.
    """
    if sweep_event_ts is None:
        return False
    if max_window_minutes <= 0:
        return False
    window_start = current_ts - timedelta(minutes=max_window_minutes)
    # Sweep must be strictly past window_start and at or before current_ts.
    return window_start < sweep_event_ts <= current_ts
