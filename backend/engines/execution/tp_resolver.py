"""Take-profit resolver — shared brick of the execution layer.

Option A v2 O1.2. Resolves the TP price for a setup given the playbook's
`take_profit_logic` configuration.

Stable signature so future `draw_type` values (swing_k1, swing_k9, vwap_band_*,
market_profile_*) can be added without breaking callers. In this sprint only
two values are wired through:
    - `fixed_rr`        : entry + tp1_rr × sl_distance (legacy, backcompat).
    - `liquidity_draw`  : next structure pivot in the direction of the trade.
                          `draw_type` ∈ {`swing_k3`, `swing_k9`} — picks the
                          corresponding pivot scale from `structure_pivots`.
                          Other keys raise so they cannot be silently used.

`pool_selection` (2026-04-22, Option \u03b1''): controls which pivot is picked
when several candidates are eligible. Two modes:
    - "nearest"     : legacy default. Picks the pivot *closest* to entry
                      (`min` price for LONG, `max` price for SHORT). This is
                      semantically "draw to first pool" but proved incompatible
                      with MASTER ICT intent (see alpha_tp_tuning_verdict.md).
    - "significant" : new. Picks the *farthest* pivot inside the acceptable
                      band [min_rr_floor \u00d7 sl_dist, max_rr_ceiling \u00d7 sl_dist].
                      Aligns with "draw to significant liquidity" (prior swing
                      high, previous day high). Requires `max_rr_ceiling`.

Reasons returned (stable vocabulary, written into the trade journal):
    - "fixed_rr"
    - "liquidity_draw_swing_k3" | "liquidity_draw_swing_k9"
    - "fallback_rr_no_pool"                  (no pivot in the direction)
    - "fallback_rr_min_floor_binding"        (nearest pool is under the floor)
    - "fallback_rr_pool_beyond_ceiling"      ("significant" mode only: all
                                              pools are farther than the
                                              max_rr_ceiling band)
    - "reject_on_fallback_no_pool"            (Option \u03b5, 2026-04-22: only
    - "reject_on_fallback_below_floor"         emitted when tp_logic_params
    - "reject_on_fallback_beyond_ceiling"      has reject_on_fallback=True.
                                               Setup engine detects the
                                               "reject_" prefix and drops the
                                               candidate — the trade is never
                                               taken. tp_price field is a
                                               sentinel (legacy fallback_rr),
                                               never read by the caller.)

The resolver does not re-compute pivots \u2014 callers hand in a pre-computed
`structure_pivots` mapping (cache-friendly, shared with future features).
"""

from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

from engines.features.pivot import Pivot

_DIRECTION_LONG = "LONG"
_DIRECTION_SHORT = "SHORT"

_ALLOWED_TP_LOGIC = {"fixed_rr", "liquidity_draw"}
_ALLOWED_DRAW_TYPES = {"swing_k3", "swing_k9"}
_DRAW_TYPE_TO_PIVOT_KEY = {"swing_k3": "k3", "swing_k9": "k9"}
_ALLOWED_POOL_SELECTION = {"nearest", "significant"}

# Defaults chosen to match the plan's YAML shape and stay safe if a caller
# omits them. They mirror backend/knowledge/campaigns/aplus03_v2.yml.
_DEFAULT_LOOKBACK_BARS = 60
_DEFAULT_MIN_RR_FLOOR = 0.5
_DEFAULT_FALLBACK_RR = 2.0
_DEFAULT_POOL_SELECTION = "nearest"  # legacy behavior; \u03b1'' YAMLs opt into "significant"


def resolve_tp_price(
    *,
    tp_logic: str,
    tp_logic_params: Optional[Mapping[str, Any]],
    tp1_rr: float,
    entry_price: float,
    sl_price: float,
    direction: str,
    bars: Sequence[Any],
    structure_pivots: Optional[Mapping[str, Sequence[Pivot]]] = None,
) -> tuple[float, str]:
    """Return `(tp_price, reason)`.

    Args:
        tp_logic: one of `fixed_rr`, `liquidity_draw`.
        tp_logic_params: opaque YAML dict (see module docstring).
        tp1_rr: legacy fixed-RR multiple (used by `fixed_rr` and as sanity input).
        entry_price: the resolved entry (post entry_gate).
        sl_price: the resolved stop-loss (structural SL from setup_engine_v2).
        direction: `LONG` or `SHORT` (case-insensitive accepted).
        bars: setup-TF bars aligned with `structure_pivots` indices. Used for
              the `lookback_bars` window check only; the resolver does not scan
              OHLC itself.
        structure_pivots: mapping `"k1"|"k3"|"k9" -> list[Pivot]` produced by
              `features.directional_change.detect_structure_multi_scale`.
    """
    if tp_logic not in _ALLOWED_TP_LOGIC:
        raise ValueError(
            f"tp_logic={tp_logic!r} not supported in this sprint "
            f"(allowed: {sorted(_ALLOWED_TP_LOGIC)})"
        )

    dir_up = direction.upper()
    if dir_up not in (_DIRECTION_LONG, _DIRECTION_SHORT):
        raise ValueError(f"direction={direction!r} must be LONG or SHORT")

    sl_distance = abs(entry_price - sl_price)
    if sl_distance <= 0:
        raise ValueError("sl_distance must be > 0")

    if tp_logic == "fixed_rr":
        return _fixed_rr(entry_price, sl_distance, tp1_rr, dir_up), "fixed_rr"

    # tp_logic == "liquidity_draw"
    params = dict(tp_logic_params or {})
    draw_type = params.get("draw_type", "swing_k3")
    if draw_type not in _ALLOWED_DRAW_TYPES:
        raise ValueError(
            f"draw_type={draw_type!r} not supported in this sprint "
            f"(allowed: {sorted(_ALLOWED_DRAW_TYPES)})"
        )

    lookback_bars = int(params.get("lookback_bars", _DEFAULT_LOOKBACK_BARS))
    min_rr_floor = float(params.get("min_rr_floor", _DEFAULT_MIN_RR_FLOOR))
    fallback_rr = float(params.get("fallback_rr", _DEFAULT_FALLBACK_RR))
    pool_selection = params.get("pool_selection", _DEFAULT_POOL_SELECTION)
    if pool_selection not in _ALLOWED_POOL_SELECTION:
        raise ValueError(
            f"pool_selection={pool_selection!r} not supported "
            f"(allowed: {sorted(_ALLOWED_POOL_SELECTION)})"
        )
    max_rr_ceiling_raw = params.get("max_rr_ceiling")
    if pool_selection == "significant" and max_rr_ceiling_raw is None:
        raise ValueError(
            "pool_selection='significant' requires 'max_rr_ceiling' in tp_logic_params"
        )
    max_rr_ceiling = (
        float(max_rr_ceiling_raw) if max_rr_ceiling_raw is not None else None
    )
    reject_on_fallback = bool(params.get("reject_on_fallback", False))

    # draw_type -> pivot scale (k3 or k9).
    pivot_key = _DRAW_TYPE_TO_PIVOT_KEY[draw_type]
    pivots: Sequence[Pivot] = ()
    if structure_pivots is not None:
        pivots = structure_pivots.get(pivot_key, ()) or ()

    last_bar_idx = len(bars) - 1
    window_start = last_bar_idx - lookback_bars  # inclusive low bound

    pool_price, verdict = _select_pool(
        pivots,
        entry_price=entry_price,
        sl_distance=sl_distance,
        direction=dir_up,
        window_start=window_start,
        min_rr_floor=min_rr_floor,
        max_rr_ceiling=max_rr_ceiling,
        pool_selection=pool_selection,
    )

    if reject_on_fallback and verdict != "pool":
        # Option \u03b5 (2026-04-22): the playbook opts into hard reject when the
        # resolver cannot place a liquidity_draw target in the acceptable band.
        # The returned tp_price is a sentinel (legacy fallback_rr) so the
        # signature stays (float, str); setup_engine_v2 checks the "reject_"
        # prefix and drops the setup before the price is consumed.
        return (
            _tp_from_rr(entry_price, sl_distance, fallback_rr, dir_up),
            f"reject_on_fallback_{verdict}",
        )

    if verdict == "no_pool":
        return (
            _tp_from_rr(entry_price, sl_distance, fallback_rr, dir_up),
            "fallback_rr_no_pool",
        )
    if verdict == "beyond_ceiling":
        return (
            _tp_from_rr(entry_price, sl_distance, fallback_rr, dir_up),
            "fallback_rr_pool_beyond_ceiling",
        )
    if verdict == "below_floor":
        floor_price = _tp_from_rr(entry_price, sl_distance, min_rr_floor, dir_up)
        return floor_price, "fallback_rr_min_floor_binding"

    # verdict == "pool" \u2014 explicit pool selected.
    assert pool_price is not None
    return pool_price, f"liquidity_draw_{draw_type}"


def _fixed_rr(entry: float, sl_dist: float, rr: float, direction: str) -> float:
    return _tp_from_rr(entry, sl_dist, rr, direction)


def _tp_from_rr(entry: float, sl_dist: float, rr: float, direction: str) -> float:
    if direction == _DIRECTION_LONG:
        return entry + sl_dist * rr
    return entry - sl_dist * rr


def _select_pool(
    pivots: Sequence[Pivot],
    *,
    entry_price: float,
    sl_distance: float,
    direction: str,
    window_start: int,
    min_rr_floor: float,
    max_rr_ceiling: Optional[float],
    pool_selection: str,
) -> tuple[Optional[float], str]:
    """Select a liquidity pool pivot for TP placement.

    Returns `(price, verdict)` where verdict is one of:
        - "pool"           : pool selected, price is the TP
        - "no_pool"        : no pivot in the trade direction within lookback
        - "below_floor"    : every candidate would give R < min_rr_floor
        - "beyond_ceiling" : every candidate would give R > max_rr_ceiling
                             ("significant" mode only)

    Selection rules:
        - "nearest"     : pick pivot closest to entry, strictly beyond entry.
                          Legacy behavior. If the pick sits below floor \u2192
                          below_floor. `max_rr_ceiling` is ignored.
        - "significant" : filter pivots whose R distance sits in the band
                          [min_rr_floor, max_rr_ceiling], pick the farthest
                          (highest R) from entry. If none in band, decide
                          below_floor or beyond_ceiling by looking at *all*
                          pivots in direction.
    """
    if not pivots:
        return None, "no_pool"

    # Collect in-direction pivots inside the lookback window.
    if direction == _DIRECTION_LONG:
        in_dir = [
            p.price
            for p in pivots
            if p.type == "high" and p.index >= window_start and p.price > entry_price
        ]
    else:
        in_dir = [
            p.price
            for p in pivots
            if p.type == "low" and p.index >= window_start and p.price < entry_price
        ]

    if not in_dir:
        return None, "no_pool"

    floor_price = _tp_from_rr(entry_price, sl_distance, min_rr_floor, direction)

    if pool_selection == "nearest":
        pick = min(in_dir) if direction == _DIRECTION_LONG else max(in_dir)
        if _closer_to_entry_than(pick, floor_price, direction=direction):
            return None, "below_floor"
        return pick, "pool"

    # pool_selection == "significant"
    assert max_rr_ceiling is not None
    ceiling_price = _tp_from_rr(
        entry_price, sl_distance, max_rr_ceiling, direction
    )
    in_band = [
        p
        for p in in_dir
        if not _closer_to_entry_than(p, floor_price, direction=direction)
        and not _farther_from_entry_than(p, ceiling_price, direction=direction)
    ]
    if in_band:
        # Farthest from entry = highest for LONG, lowest for SHORT.
        pick = max(in_band) if direction == _DIRECTION_LONG else min(in_band)
        return pick, "pool"

    # No pool in band: classify why. Prefer "below_floor" if ANY pool is below
    # the floor (common case: nearby micro-pivot); else "beyond_ceiling".
    any_below_floor = any(
        _closer_to_entry_than(p, floor_price, direction=direction) for p in in_dir
    )
    if any_below_floor:
        return None, "below_floor"
    return None, "beyond_ceiling"


def _closer_to_entry_than(
    candidate: float, reference: float, *, direction: str
) -> bool:
    """True if `candidate` price sits closer to entry than `reference`
    (i.e. would give a smaller R)."""
    if direction == _DIRECTION_LONG:
        return candidate < reference
    return candidate > reference


def _farther_from_entry_than(
    candidate: float, reference: float, *, direction: str
) -> bool:
    """True if `candidate` price sits farther from entry than `reference`
    (i.e. would give a larger R)."""
    if direction == _DIRECTION_LONG:
        return candidate > reference
    return candidate < reference
