"""SMT HTF-anchored cross-index divergence detector — §0.B.2 brique canon.

Source : MASTER ligne 12745-12841 (SMT verbatim) + TRUE `FJch02ucIO8`
("One Simple Confluence") + `7dTQA0t8SH0` (SMT Divergence Explained) +
`ironJFzNBic` (HTF bias SMT component). Convergence 3-corpus 100%.

Mechanism (canon, TRUE `FJch02ucIO8`) :
    Two correlated indices (SPY/QQQ) post pool-sweep HTF (4h/1h). At the
    sweep moment, one index breaks structure counter to the prior trend
    (HL in downtrend, LH in uptrend) — this is the **leading** index.
    The other index continues the trend — this is the **lagging** index.
    The trade: enter **lagging** in the direction **of the leading's counter-
    move** (divergence signals exhaustion). TP = "SMT completion" = the
    attached swing H/L that was the origin of the swept pool (price
    typically retraces to that level as the divergence resolves).

This module is a **gate** (not a scoring bonus). Wiring : playbook YAML
`required_signals: [smt_divergence_cross_index]`. Depréciates the legacy
`detect_smt` in custom_detectors.py (rolling max/min 1h non-anchored,
scoring only). Legacy kept for backward compat of scoring_v1 playbooks.

Contract :
    detect_smt_divergence(a, b, detection_ts, sweep_ts=None) -> SMTSignal | None
    SMTInputs holds per-instrument state (pivots k3, last close, attached
    swing price from pool origin analysis).
    SMTSignal.smt_completion_target → feeds tp_resolver tp_logic="smt_completion"
    via tp_logic_params["smt_completion_price"].

Integration with §0.B briques :
    §0.B.7 PoolFreshnessTracker → flags which HTF pool just got swept.
    §0.B.3 htf_bias_structure → provides the attached swing price (from
        the FVG/pool origin in HTF structure).
    §0.B.1 tp_resolver → consumes smt_completion_target as TP.

No dependency on actual OHLC here — pure logic on Pivot sequences + closes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Optional, Sequence

from engines.features.pivot import Pivot


_PivotType = Literal["high", "low"]


@dataclass(frozen=True)
class SMTInputs:
    """Per-instrument inputs at detection time.

    `pivots_k3` : k3-scale pivots up to detection_ts (from
        `features.directional_change.detect_structure_multi_scale`).
        Must be in chronological order (ascending index).
    `last_close` : most recent close price for this instrument.
    `attached_swing_price` : the origin swing H/L of the pool swept on this
        instrument. Supplied by §0.B.3 htf_bias_structure analysis when a
        pool is marked swept via §0.B.7 PoolFreshnessTracker. None if this
        instrument did not sweep a pool (i.e. is the lagging candidate
        only — attached swing only relevant for leading index).
    """

    symbol: str
    pivots_k3: Sequence[Pivot]
    last_close: float
    attached_swing_price: Optional[float] = None


@dataclass(frozen=True)
class SMTSignal:
    """Emitted SMT divergence event — consumed as entry gate by playbook."""

    detected_ts: datetime
    leading_symbol: str
    lagging_symbol: str
    # Direction for the **lagging** instrument's trade.
    # bearish divergence (leading made LH) → trade SHORT lagging.
    # bullish divergence (leading made HL) → trade LONG lagging.
    direction: Literal["LONG", "SHORT"]
    divergence_type: Literal["bull", "bear"]
    lagging_entry_reference: float  # lagging instrument's last_close (reference)
    smt_completion_target: float  # leading's attached_swing_price (TP)
    lead_pivot_price: float  # the LH/HL k3 pivot price that triggered
    lead_pivot_ts: datetime
    prev_same_type_pivot_price: float  # the previous same-type pivot to compare


def classify_last_pivot(
    pivots: Sequence[Pivot],
    *,
    since_ts: Optional[datetime] = None,
) -> Optional[Literal["HH", "LH", "HL", "LL"]]:
    """Classify the latest pivot vs the previous same-type pivot.

    Returns one of:
        "HH" — latest high pivot > previous high pivot (continuation up)
        "LH" — latest high pivot < previous high pivot (bearish divergence)
        "HL" — latest low pivot > previous low pivot (bullish divergence)
        "LL" — latest low pivot < previous low pivot (continuation down)
        None — insufficient data (fewer than 2 same-type pivots), or the
               latest pivot is before `since_ts`.

    `since_ts` (optional) : if provided, only consider pivots whose
        timestamp is >= since_ts. Used to restrict to post-sweep pivots.
    """
    if len(pivots) < 2:
        return None
    # Filter to relevant window.
    if since_ts is not None:
        pivots = [p for p in pivots if p.timestamp >= since_ts]
    if len(pivots) < 2:
        return None

    latest = pivots[-1]
    # Find the previous pivot of same type.
    prev_same_type: Optional[Pivot] = None
    for p in reversed(pivots[:-1]):
        if p.type == latest.type:
            prev_same_type = p
            break
    if prev_same_type is None:
        return None

    if latest.type == "high":
        return "HH" if latest.price > prev_same_type.price else "LH"
    return "HL" if latest.price > prev_same_type.price else "LL"


def _get_latest_pivot_with_predecessor(
    pivots: Sequence[Pivot],
    *,
    since_ts: Optional[datetime] = None,
) -> Optional[tuple[Pivot, Pivot]]:
    """Return (latest_pivot, previous_same_type_pivot) or None."""
    window = pivots if since_ts is None else [p for p in pivots if p.timestamp >= since_ts]
    if len(window) < 2:
        return None
    latest = window[-1]
    for p in reversed(window[:-1]):
        if p.type == latest.type:
            return latest, p
    return None


def detect_smt_divergence(
    *,
    a: SMTInputs,
    b: SMTInputs,
    detection_ts: datetime,
    sweep_ts: Optional[datetime] = None,
) -> Optional[SMTSignal]:
    """Detect SMT divergence between two correlated instruments.

    Returns an `SMTSignal` if a valid divergence is detected, else `None`.

    The detection requires, post-sweep (or unconditionally if sweep_ts is None):
      - Each instrument has at least 2 same-type k3 pivots.
      - The two instruments show **divergent** latest classifications:
          leading = LH while lagging = HH (bearish divergence — pool HIGH swept)
          leading = HL while lagging = LL (bullish divergence — pool LOW swept)
      - The **leading** instrument must have `attached_swing_price` populated
        (this becomes the smt_completion_target for the lagging's trade).

    If both instruments classify identically (both HH, both LH, etc.), no
    divergence — return None. If a lagging/leading pair cannot be determined
    unambiguously, return None (no arbitrary tie-break).
    """
    a_class = classify_last_pivot(a.pivots_k3, since_ts=sweep_ts)
    b_class = classify_last_pivot(b.pivots_k3, since_ts=sweep_ts)
    if a_class is None or b_class is None:
        return None
    if a_class == b_class:
        return None  # no divergence

    # --- Bearish divergence: one LH, the other HH ---
    if {a_class, b_class} == {"LH", "HH"}:
        leading, lagging = (a, b) if a_class == "LH" else (b, a)
        if leading.attached_swing_price is None:
            return None
        lead_pair = _get_latest_pivot_with_predecessor(
            leading.pivots_k3, since_ts=sweep_ts
        )
        if lead_pair is None:
            return None
        lead_latest, lead_prev = lead_pair
        return SMTSignal(
            detected_ts=detection_ts,
            leading_symbol=leading.symbol,
            lagging_symbol=lagging.symbol,
            direction="SHORT",
            divergence_type="bear",
            lagging_entry_reference=lagging.last_close,
            smt_completion_target=leading.attached_swing_price,
            lead_pivot_price=lead_latest.price,
            lead_pivot_ts=lead_latest.timestamp,
            prev_same_type_pivot_price=lead_prev.price,
        )

    # --- Bullish divergence: one HL, the other LL ---
    if {a_class, b_class} == {"HL", "LL"}:
        leading, lagging = (a, b) if a_class == "HL" else (b, a)
        if leading.attached_swing_price is None:
            return None
        lead_pair = _get_latest_pivot_with_predecessor(
            leading.pivots_k3, since_ts=sweep_ts
        )
        if lead_pair is None:
            return None
        lead_latest, lead_prev = lead_pair
        return SMTSignal(
            detected_ts=detection_ts,
            leading_symbol=leading.symbol,
            lagging_symbol=lagging.symbol,
            direction="LONG",
            divergence_type="bull",
            lagging_entry_reference=lagging.last_close,
            smt_completion_target=leading.attached_swing_price,
            lead_pivot_price=lead_latest.price,
            lead_pivot_ts=lead_latest.timestamp,
            prev_same_type_pivot_price=lead_prev.price,
        )

    # Other combinations (HH/HL, LL/LH, etc.) are not the canonical SMT pattern
    # (same-directional bias). No signal.
    return None
