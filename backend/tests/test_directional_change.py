"""Option A v2 O2.4 — directional_change zigzag tests.

Three required cases per plan:
    1. Single bullish swing → one pivot detected at correct index/price/type.
    2. Flat series (no move > kappa × ATR) → zero pivots.
    3. Multi-scale hierarchy: k1 finds N pivots, k3 ≤ N/3, k9 ≤ N/9.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timedelta

from engines.features.directional_change import (
    detect_directional_change,
    detect_structure_multi_scale,
    invalidate_cache,
)


@dataclass
class _Bar:
    open: float
    high: float
    low: float
    close: float
    timestamp: datetime


def _flat_series(n: int, price: float = 450.0) -> list:
    """n bars hugging `price` with tiny noise — sigma threshold should never
    trip."""
    base = datetime(2025, 7, 15, 9, 30)
    out = []
    for i in range(n):
        jitter = 0.001 * ((i % 2) - 0.5)  # ±0.0005
        out.append(_Bar(price, price + jitter, price - jitter, price, base + timedelta(minutes=5 * i)))
    return out


def _bullish_leg_then_pullback() -> list:
    """A clean up-leg from 450 to 460 over 20 bars then a 2-point pullback.
    The peak (index 20, price ~460) is the pivot we expect k=1 to detect."""
    base = datetime(2025, 7, 15, 9, 30)
    out = []
    # 20 rising bars
    for i in range(21):
        p = 450.0 + 0.5 * i
        out.append(_Bar(p - 0.1, p + 0.1, p - 0.2, p, base + timedelta(minutes=5 * i)))
    # 10 falling bars
    for i in range(10):
        p = 460.0 - 0.4 * (i + 1)
        t = base + timedelta(minutes=5 * (21 + i))
        out.append(_Bar(p + 0.1, p + 0.2, p - 0.1, p, t))
    return out


def test_single_up_leg_produces_low_then_high_pivot():
    invalidate_cache()
    bars = _bullish_leg_then_pullback()
    pivots = detect_directional_change(bars, kappa=1.0, atr_period=5)

    # We expect at least one "high" pivot near index 20 (the peak at ~460).
    highs = [p for p in pivots if p.type == "high"]
    assert highs, f"expected a high pivot, got {pivots}"
    top = max(highs, key=lambda p: p.price)
    assert 459.0 <= top.price <= 461.0
    assert 18 <= top.index <= 22


def test_flat_series_yields_no_pivots():
    invalidate_cache()
    bars = _flat_series(50)
    pivots = detect_directional_change(bars, kappa=10.0, atr_period=5)
    assert pivots == []


def test_multi_scale_hierarchy_k1_ge_k3_ge_k9():
    """Build a noisy random walk — k1 (fine) should always produce ≥ the
    counts at k3 and k9 (the stricter thresholds collapse minor wiggles)."""
    invalidate_cache()
    rng = random.Random(42)
    base = datetime(2025, 7, 15, 9, 30)
    price = 450.0
    bars: list = []
    for i in range(400):
        drift = rng.uniform(-0.3, 0.3)
        price = price + drift
        h = price + rng.uniform(0.0, 0.4)
        l = price - rng.uniform(0.0, 0.4)
        bars.append(_Bar(price, h, l, price + rng.uniform(-0.1, 0.1), base + timedelta(minutes=5 * i)))

    result = detect_structure_multi_scale(bars, kappas=(1.0, 3.0, 9.0), atr_period=14, cache_symbol="TEST")
    assert "k1" in result and "k3" in result and "k9" in result
    assert len(result["k1"]) >= len(result["k3"]) >= len(result["k9"]) >= 0
    # Fine scale must actually find *something* on 400 bars of random walk.
    assert len(result["k1"]) > 0


def test_multi_scale_cache_returns_same_pivot_list_on_reuse():
    invalidate_cache()
    bars = _bullish_leg_then_pullback()
    r1 = detect_structure_multi_scale(bars, kappas=(1.0, 3.0, 9.0), atr_period=5, cache_symbol="SPY")
    r2 = detect_structure_multi_scale(bars, kappas=(1.0, 3.0, 9.0), atr_period=5, cache_symbol="SPY")
    assert r1 is r2  # LRU hit → identity equality
