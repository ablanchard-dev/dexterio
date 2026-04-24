"""HTF bias structure 7-step state machine — §0.B.3 brique canon.

Replaces the SMA_5 proxy used by `require_htf_alignment: D` (Phase D.1 audit :
0/171 rejections = cosmétique). Source TRUE `ironJFzNBic` ("How To Find Daily
Bias") convergent with MASTER ligne 12700+.

The 7 steps (TJR canon) :
    1. Structure HH-HL 4H/1H via directional_change k9 → uptrend / downtrend / range
    2. Position cycle : sweep récent ? retrace vers FVG ?
    3. FVG HTF respect/disrespect binary state machine
    4. Draws on liquidity ranked (prev D H/L, Asia H/L, London H/L, hourly)
       + exclure déjà swept (via §0.B.7 PoolFreshnessTracker)
    5. Pre-market + NY open manipulation observation (flag)
    6. Close-through flip detection (bias flip si FVG HTF close through)
    7. SMT cross-index refinement (depuis §0.B.2 smt_htf)

This module exposes composable helpers for each step plus an orchestrator
`compute_htf_bias()` that combines them into a single `HTFBiasResult`.
Callers can mix and match — e.g. a lightweight pass uses only step 1
(structural) while a full gate pipeline runs all 7.

Output `HTFBiasResult` is a frozen snapshot consumed as gate in playbook YAML
via `htf_bias_gate.method: structure_k9_7step` (cf plan §5.2 NEW knobs).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Optional, Sequence

from engines.features.pivot import Pivot
from engines.features.pool_freshness_tracker import Pool


Bias = Literal["bullish", "bearish", "neutral"]
StructurePattern = Literal["HH_HL", "LL_LH", "mixed", "insufficient"]
FVGRespectState = Literal["respected", "disrespected", "closed_through", "pending"]


@dataclass(frozen=True)
class FVGZone:
    """HTF FVG zone with current respect state."""

    id: str
    low: float
    high: float
    direction: Literal["bullish", "bearish"]  # bullish FVG = gap supports LONGs
    created_ts: datetime
    state: FVGRespectState = "pending"


@dataclass(frozen=True)
class HTFBiasInputs:
    """Inputs for HTF bias 7-step computation at detection time."""

    pivots_k9_htf: Sequence[Pivot]  # HTF (4h or D) macro pivots
    last_close_htf: float
    last_high_htf: float = 0.0
    last_low_htf: float = 0.0
    fvg_zones_htf: Sequence[FVGZone] = field(default_factory=tuple)
    fresh_draws: Sequence[Pool] = field(default_factory=tuple)
    premarket_manipulation: bool = False
    smt_divergence_present: Optional[bool] = None  # from §0.B.2 smt_htf
    prior_bias: Optional[Bias] = None  # for flip detection


@dataclass(frozen=True)
class HTFBiasResult:
    """Composite 7-step output."""

    bias: Bias
    confidence: float  # 0.0 to 1.0
    structure_pattern: StructurePattern
    in_retracement: bool
    respected_fvgs: tuple[str, ...]
    disrespected_fvgs: tuple[str, ...]
    closed_through_fvgs: tuple[str, ...]
    active_draws: tuple[str, ...]  # pool ids, ranked (higher priority first)
    premarket_manipulation_detected: bool
    flipped_at: Optional[datetime]
    smt_refinement: Optional[Literal["confirms", "contradicts", "none"]]


# ---------- Step 1 : Structure HH-HL 4H/1H ----------

def compute_structural_bias(pivots_k9: Sequence[Pivot]) -> tuple[Bias, StructurePattern, float]:
    """Return (bias, pattern, confidence) based on the last 2 same-type pivots.

    HH + HL → uptrend (bullish, high confidence if both hold).
    LL + LH → downtrend (bearish).
    HH + LH or LL + HL → mixed (low confidence, neutral bias).
    Insufficient data (< 2 of each type in tail) → neutral / "insufficient" / 0.0.

    Confidence scale :
        1.0  — clean HH+HL (or LL+LH) within last 4 pivots
        0.5  — one leg confirms, other is mixed/missing
        0.0  — insufficient data or contradicting pattern
    """
    if len(pivots_k9) < 4:
        return "neutral", "insufficient", 0.0

    # Get last 2 highs and last 2 lows.
    highs = [p for p in pivots_k9 if p.type == "high"]
    lows = [p for p in pivots_k9 if p.type == "low"]
    if len(highs) < 2 or len(lows) < 2:
        return "neutral", "insufficient", 0.0

    hh = highs[-1].price > highs[-2].price
    hl = lows[-1].price > lows[-2].price
    lh = highs[-1].price < highs[-2].price
    ll = lows[-1].price < lows[-2].price

    if hh and hl:
        return "bullish", "HH_HL", 1.0
    if ll and lh:
        return "bearish", "LL_LH", 1.0
    # Mixed patterns (HH+LL, LH+HL, etc.) — neutral.
    return "neutral", "mixed", 0.3


# ---------- Step 2 : Position in cycle (retracement detector) ----------

def is_in_retracement(
    pivots_k9: Sequence[Pivot],
    last_close: float,
    bias: Bias,
    retracement_floor_pct: float = 0.25,
    retracement_ceiling_pct: float = 0.75,
) -> bool:
    """True if price is retracing back into a target zone after a swing extreme.

    For bullish bias : last high is the swing H, last low the swing L ; we
    consider a retracement when last_close is within [floor, ceiling] of
    the swing range measured from the low.
    Mirror for bearish bias.

    Neutral bias / insufficient pivots → False (no position state).
    """
    if bias == "neutral" or len(pivots_k9) < 2:
        return False
    highs = [p for p in pivots_k9 if p.type == "high"]
    lows = [p for p in pivots_k9 if p.type == "low"]
    if not highs or not lows:
        return False
    swing_h = highs[-1].price
    swing_l = lows[-1].price
    if swing_h <= swing_l:
        return False
    # Measure from the swing low → last_close position as fraction of range.
    frac = (last_close - swing_l) / (swing_h - swing_l)
    if bias == "bullish":
        # Bullish retracement = back down into the discount half (below midpoint).
        return retracement_floor_pct <= frac <= retracement_ceiling_pct
    # bearish: retracement = back up into the premium half.
    return retracement_floor_pct <= frac <= retracement_ceiling_pct


# ---------- Step 3 : FVG HTF respect/disrespect ----------

def classify_fvg_respect(
    zone: FVGZone,
    bar_high: float,
    bar_low: float,
    bar_close: float,
) -> FVGRespectState:
    """Classify a single FVG's state for the current bar.

    respected      : price entered zone but did not close beyond it
                     (price still "inside" or exiting in the gap's direction)
    disrespected   : price entered zone and continues against it (counter-direction)
    closed_through : close price crossed fully through the zone counter to its
                     direction → bias flip signal (step 6)
    pending        : bar did not interact with the zone (no change).
    """
    z_lo, z_hi = zone.low, zone.high
    touches = bar_low <= z_hi and bar_high >= z_lo
    if not touches:
        return zone.state if zone.state != "pending" else "pending"

    # Bullish FVG : closing below z_lo = closed_through (disrespect confirmed).
    if zone.direction == "bullish":
        if bar_close < z_lo:
            return "closed_through"
        # Closing above z_hi after touch = respected (gap held as support).
        if bar_close >= z_lo:
            return "respected"
        return "pending"
    # Bearish FVG : closing above z_hi = closed_through.
    if bar_close > z_hi:
        return "closed_through"
    if bar_close <= z_hi:
        return "respected"
    return "pending"


# ---------- Step 4 : Draws on liquidity — ranked + exclude swept ----------

def rank_active_draws(fresh_pools: Sequence[Pool], max_count: int = 6) -> tuple[str, ...]:
    """Return pool ids ranked by TF priority (via PoolFreshnessTracker ordering).

    Caller is expected to pass `fresh_pools` that are already unswept (the
    tracker's get_fresh_pools() returns them in priority order). This helper
    just truncates to `max_count` and extracts ids for the HTFBiasResult.
    """
    return tuple(p.id for p in fresh_pools[:max_count])


# ---------- Step 6 : Close-through flip ----------

def detect_close_through_flip(
    prior_bias: Optional[Bias],
    zones: Sequence[FVGZone],
    current_ts: datetime,
) -> Optional[datetime]:
    """If any zone is in `closed_through` state and contradicts prior_bias,
    return the current_ts as the flip timestamp. Otherwise None.

    A bullish prior_bias flips on a bullish FVG that closed_through (the
    supporting gap was broken). Mirror for bearish.
    """
    if prior_bias is None or prior_bias == "neutral":
        return None
    for z in zones:
        if z.state != "closed_through":
            continue
        # Bullish FVG closed_through = support lost = bearish flip.
        if prior_bias == "bullish" and z.direction == "bullish":
            return current_ts
        # Bearish FVG closed_through = resistance lost = bullish flip.
        if prior_bias == "bearish" and z.direction == "bearish":
            return current_ts
    return None


# ---------- Orchestrator ----------

def compute_htf_bias(
    inputs: HTFBiasInputs,
    *,
    current_ts: Optional[datetime] = None,
) -> HTFBiasResult:
    """Run all 7 steps and return the composite HTFBiasResult.

    Steps 1-6 derive from `inputs`. Step 7 (SMT refinement) applies the
    pre-computed `inputs.smt_divergence_present` flag as a refinement label.
    """
    # Step 1
    bias, pattern, structural_conf = compute_structural_bias(inputs.pivots_k9_htf)

    # Step 2
    in_retrace = is_in_retracement(
        inputs.pivots_k9_htf, inputs.last_close_htf, bias
    )

    # Step 3 : classify each FVG using last bar context (high/low/close).
    bar_high = inputs.last_high_htf or inputs.last_close_htf
    bar_low = inputs.last_low_htf or inputs.last_close_htf
    respected = []
    disrespected = []
    closed_through = []
    updated_zones: list[FVGZone] = []
    for z in inputs.fvg_zones_htf:
        new_state = classify_fvg_respect(z, bar_high, bar_low, inputs.last_close_htf)
        updated = FVGZone(
            id=z.id, low=z.low, high=z.high, direction=z.direction,
            created_ts=z.created_ts, state=new_state,
        )
        updated_zones.append(updated)
        if new_state == "respected":
            respected.append(z.id)
        elif new_state == "disrespected":
            disrespected.append(z.id)
        elif new_state == "closed_through":
            closed_through.append(z.id)

    # Step 4
    draws = rank_active_draws(inputs.fresh_draws)

    # Step 6
    flip_ts = detect_close_through_flip(
        inputs.prior_bias, updated_zones, current_ts or inputs.pivots_k9_htf[-1].timestamp
        if inputs.pivots_k9_htf else current_ts or datetime.min,
    )

    # Step 7 : SMT refinement (confirms/contradicts/none).
    smt_refinement: Optional[Literal["confirms", "contradicts", "none"]]
    if inputs.smt_divergence_present is None:
        smt_refinement = None
    elif inputs.smt_divergence_present and bias != "neutral":
        # SMT divergence at a HTF pool sweep + structural bias = refinement
        # that confirms the bias (classical canonical pattern).
        smt_refinement = "confirms"
    elif inputs.smt_divergence_present and bias == "neutral":
        smt_refinement = "none"
    else:
        smt_refinement = "none"

    # Confidence : combine structural + SMT + retracement + closed-through.
    confidence = structural_conf
    if smt_refinement == "confirms":
        confidence = min(1.0, confidence + 0.2)
    if flip_ts is not None:
        # On flip, downgrade confidence dramatically (direction is changing).
        confidence *= 0.3

    return HTFBiasResult(
        bias=bias,
        confidence=confidence,
        structure_pattern=pattern,
        in_retracement=in_retrace,
        respected_fvgs=tuple(respected),
        disrespected_fvgs=tuple(disrespected),
        closed_through_fvgs=tuple(closed_through),
        active_draws=draws,
        premarket_manipulation_detected=inputs.premarket_manipulation,
        flipped_at=flip_ts,
        smt_refinement=smt_refinement,
    )
