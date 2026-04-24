"""Daily profile 3-classification — §0.B.6 brique canon top-layer overlay.

Source : MASTER seul (ligne 13600+, 3 daily profiles non documentés dans TRUE
ou QUANT). Filter top-layer pour pré-qualifier les sessions où un playbook
should fire, basé sur la structure observée de la session elle-même et/ou
de la session précédente.

The 3 profiles (MASTER canon) :
    consolidation           : session range-bound, low directional move,
                              low volatility. Typically a non-fertile day for
                              ICT reversal setups.
    manipulation_reversal   : first half of session pushes toward an extreme
                              (manipulation), second half reverses through the
                              open in the opposite direction. Classical fertile
                              profile for ICT reversal playbooks.
    manipulation_reversal_continuation
                            : today continues the reversal direction established
                              by the previous session's manipulation_reversal.
                              Requires `prev_profile == "manipulation_reversal"`
                              AND today's direction aligning with prev's
                              reversal_direction.

Usage : overlay top-layer `required_daily_profile: [manipulation_reversal,
manipulation_reversal_continuation]`. Playbook YAML specifies which profiles
it wants to trade ; the gate rejects setups on sessions classified otherwise.

Contract :
    classify_session_profile(bars, prev_profile_snapshot, atr) -> SessionProfile
    is_profile_allowed(profile, allowed_list) -> bool

Implementation note : classification is partial-session capable — it can be
called with fewer bars than a full session (e.g. 30m into the day) and return
"undetermined" until enough structure is observed. Callers typically re-
classify at each new bar (cheap : pure function on N bars).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Optional, Sequence


DailyProfile = Literal[
    "consolidation",
    "manipulation_reversal",
    "manipulation_reversal_continuation",
    "undetermined",
]
ReversalDirection = Literal["up", "down"]


@dataclass(frozen=True)
class SessionProfileSnapshot:
    """Frozen classification of a session (full or partial)."""

    profile: DailyProfile
    confidence: float  # 0.0 to 1.0
    session_open: float
    session_close: float
    session_high: float
    session_low: float
    manipulation_extreme: Optional[float] = None
    reversal_direction: Optional[ReversalDirection] = None


def classify_session_profile(
    bars: Sequence[Any],
    *,
    prev_profile: Optional[SessionProfileSnapshot] = None,
    atr: float = 0.0,
    consolidation_max_range_atr_mult: float = 1.5,
    min_bars_required: int = 4,
) -> SessionProfileSnapshot:
    """Classify the session formed by `bars` into one of the 3 profiles.

    bars : chronological sequence with .open/.high/.low/.close attributes.
    prev_profile : classification of the prior session (for continuation).
    atr : reference volatility (session-scale ATR or analogous). If 0, the
        consolidation branch falls back to a pure directional-move test.
    consolidation_max_range_atr_mult : session is consolidation if its range
        is < consolidation_max_range_atr_mult × atr AND |close - open| <
        0.3 × range.
    min_bars_required : below this count → undetermined (partial session
        without enough structure).
    """
    if len(bars) < min_bars_required:
        return SessionProfileSnapshot(
            profile="undetermined",
            confidence=0.0,
            session_open=float(bars[0].open) if bars else 0.0,
            session_close=float(bars[-1].close) if bars else 0.0,
            session_high=max((float(b.high) for b in bars), default=0.0),
            session_low=min((float(b.low) for b in bars), default=0.0),
        )

    session_open = float(bars[0].open)
    session_close = float(bars[-1].close)
    session_high = max(float(b.high) for b in bars)
    session_low = min(float(b.low) for b in bars)
    rng = session_high - session_low
    directional_move = abs(session_close - session_open)

    # --- Consolidation branch ---
    # Small directional move AND tight range (relative to ATR if provided).
    is_tight_directional = rng > 0 and directional_move < 0.3 * rng
    if atr > 0:
        is_tight_range = rng < consolidation_max_range_atr_mult * atr
    else:
        # Fallback without ATR reference : use directional move only.
        is_tight_range = True
    if is_tight_directional and is_tight_range:
        return SessionProfileSnapshot(
            profile="consolidation",
            confidence=0.7,
            session_open=session_open,
            session_close=session_close,
            session_high=session_high,
            session_low=session_low,
        )

    # --- Manipulation-reversal branch ---
    # Split bars into first half (manipulation candidate) and second half
    # (reversal candidate). Classical canon : first half pushes toward an
    # extreme, second half reverses through the open.
    mid = len(bars) // 2
    first_high = max(float(b.high) for b in bars[:mid])
    first_low = min(float(b.low) for b in bars[:mid])

    # Manip up then reversal down :
    #   first_high > session_open + 0.15×range (meaningful push, not a wiggle)
    #   AND session_close < session_open (reversed down)
    #   AND first_high >= session_high (first-half is the extreme).
    # The 0.15×range threshold prevents normal opening-bar wicks from being
    # misclassified as manipulation on clean trending days.
    manip_threshold = 0.15 * rng
    manip_up_reversal_down = (
        first_high > session_open + manip_threshold
        and session_close < session_open
        and first_high >= session_high
    )
    # Manip down then reversal up : mirror.
    manip_down_reversal_up = (
        first_low < session_open - manip_threshold
        and session_close > session_open
        and first_low <= session_low
    )

    if manip_up_reversal_down:
        profile: DailyProfile = "manipulation_reversal"
        extreme = first_high
        direction: ReversalDirection = "down"
        # Continuation check : prev session was manip_reversal with same direction.
        if (
            prev_profile is not None
            and prev_profile.profile == "manipulation_reversal"
            and prev_profile.reversal_direction == "down"
        ):
            profile = "manipulation_reversal_continuation"
        return SessionProfileSnapshot(
            profile=profile,
            confidence=0.8,
            session_open=session_open,
            session_close=session_close,
            session_high=session_high,
            session_low=session_low,
            manipulation_extreme=extreme,
            reversal_direction=direction,
        )

    if manip_down_reversal_up:
        profile = "manipulation_reversal"
        extreme = first_low
        direction = "up"
        if (
            prev_profile is not None
            and prev_profile.profile == "manipulation_reversal"
            and prev_profile.reversal_direction == "up"
        ):
            profile = "manipulation_reversal_continuation"
        return SessionProfileSnapshot(
            profile=profile,
            confidence=0.8,
            session_open=session_open,
            session_close=session_close,
            session_high=session_high,
            session_low=session_low,
            manipulation_extreme=extreme,
            reversal_direction=direction,
        )

    # Neither consolidation nor clean manipulation-reversal.
    return SessionProfileSnapshot(
        profile="undetermined",
        confidence=0.0,
        session_open=session_open,
        session_close=session_close,
        session_high=session_high,
        session_low=session_low,
    )


def is_profile_allowed(
    profile: DailyProfile, allowed: Sequence[DailyProfile]
) -> bool:
    """True if `profile` is in `allowed`. Convenience for YAML gate checks."""
    return profile in allowed
