"""Tests for F2 PortfolioAllocator + backtester (pure logic)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from engines.portfolio.allocator import (
    PortfolioAllocator,
    allocate_equal_weight,
    allocate_momentum_jt,
    allocate_risk_parity,
    allocate_tsmom_signal,
    allocate_vol_target,
)
from engines.portfolio.backtester import compute_metrics, run_backtest


@pytest.fixture
def synthetic_prices() -> pd.DataFrame:
    """Synthetic 2-year daily prices for 3 tickers with distinct trends."""
    dates = pd.date_range("2023-01-01", periods=500, freq="B")
    rng = np.random.default_rng(42)
    # AAA : uptrend +0.0005/day drift
    # BBB : flat 0 drift
    # CCC : downtrend -0.0003/day drift
    a = 100.0 * np.exp(np.cumsum(0.0005 + rng.normal(0, 0.01, 500)))
    b = 100.0 * np.exp(np.cumsum(0.0 + rng.normal(0, 0.015, 500)))
    c = 100.0 * np.exp(np.cumsum(-0.0003 + rng.normal(0, 0.02, 500)))
    return pd.DataFrame({"AAA": a, "BBB": b, "CCC": c}, index=dates)


def test_equal_weight_returns_uniform_weights():
    weights = allocate_equal_weight(["A", "B", "C", "D"])
    assert weights == {"A": 0.25, "B": 0.25, "C": 0.25, "D": 0.25}


def test_momentum_jt_picks_top_n_winners(synthetic_prices):
    as_of = synthetic_prices.index[-30]  # allow skip_month window
    weights = allocate_momentum_jt(
        synthetic_prices, pd.Timestamp(as_of),
        lookback_months=6, skip_months=1, top_n=1,
    )
    # Exactly 1 winner gets weight 1.0, others 0 (top_n=1 equal-weight).
    assert sum(weights.values()) == pytest.approx(1.0)
    winners = [t for t, w in weights.items() if w > 0]
    assert len(winners) == 1
    # Winner should be one that had positive 6m-minus-1m return.
    assert weights[winners[0]] == pytest.approx(1.0)


def test_risk_parity_inverse_vol(synthetic_prices):
    weights = allocate_risk_parity(
        synthetic_prices, synthetic_prices.index[-1],
        vol_lookback_days=60,
    )
    # CCC (highest vol) should have lowest weight ; AAA lowest vol → highest.
    assert weights["AAA"] > weights["CCC"]
    assert sum(weights.values()) == pytest.approx(1.0, abs=1e-6)


def test_vol_target_caps_below_base(synthetic_prices):
    base = {"AAA": 0.5, "BBB": 0.5}
    weights = allocate_vol_target(
        synthetic_prices[["AAA", "BBB"]], synthetic_prices.index[-1],
        target_annual_vol=0.05,  # very low target → must scale down
        base_weights=base,
    )
    total = sum(weights.values())
    assert total < 1.0  # scaled down
    assert weights["AAA"] < base["AAA"]


def test_allocator_allocate_momentum_with_vol_overlay(synthetic_prices):
    alloc = PortfolioAllocator(["AAA", "BBB", "CCC"])
    result = alloc.allocate(
        synthetic_prices, synthetic_prices.index[-30],
        method="momentum", overlays=["vol_target"],
        jt_lookback=6, jt_skip=1, jt_top_n=1,
        target_annual_vol=0.10,
    )
    assert result.method == "momentum"
    total = sum(result.weights.values())
    assert total <= 1.0  # overlay may scale down
    assert result.cash_weight == pytest.approx(1.0 - total, abs=1e-6)


def test_backtest_equity_starts_at_one(synthetic_prices):
    alloc = PortfolioAllocator(["AAA", "BBB", "CCC"])
    eq, m, hist = run_backtest(
        synthetic_prices, alloc,
        method="equal_weight",
        rebalance_freq_days=21, warmup_days=60,
    )
    assert eq.iloc[0] == pytest.approx(1.0, abs=1e-6)
    assert m.n_days > 0
    assert m.n_rebalances > 0


def test_backtest_positive_trend_produces_positive_return(synthetic_prices):
    alloc = PortfolioAllocator(["AAA"])  # only the uptrend ticker
    eq, m, _ = run_backtest(
        synthetic_prices[["AAA"]], alloc,
        method="equal_weight",
        rebalance_freq_days=21, warmup_days=60,
    )
    # Monotonic uptrend synthetic → equity > 1 at end.
    assert eq.iloc[-1] > 1.0
    assert m.total_return > 0.0


def test_compute_metrics_maxdd_correct():
    # Equity : 1.0 → 1.1 → 0.9 → 1.05 → max DD = -18.18% (from 1.1 to 0.9).
    eq = pd.Series([1.0, 1.1, 0.9, 1.05],
                   index=pd.date_range("2024-01-01", periods=4, freq="D"))
    m = compute_metrics(eq)
    assert m.max_drawdown == pytest.approx(-0.1818, abs=0.01)


def test_equal_weight_sums_to_one_regardless_of_n():
    for n in [1, 2, 5, 10]:
        w = allocate_equal_weight([f"T{i}" for i in range(n)])
        assert sum(w.values()) == pytest.approx(1.0, abs=1e-9)


def test_allocator_unknown_method_raises():
    alloc = PortfolioAllocator(["AAA"])
    with pytest.raises(ValueError, match="Unknown method"):
        alloc.allocate(
            pd.DataFrame({"AAA": [100, 101]},
                         index=pd.date_range("2024-01-01", periods=2)),
            pd.Timestamp("2024-01-02"),
            method="nonexistent",
        )


# ---- TSMOM (Time-Series Momentum per-asset) tests ----


def test_tsmom_long_when_positive_return(synthetic_prices):
    """AAA has +0.0005/day drift, after 252 days r_252 > 0 → long."""
    as_of = synthetic_prices.index[-1]
    weights = allocate_tsmom_signal(
        synthetic_prices[["AAA"]], pd.Timestamp(as_of), lookback_days=252,
    )
    assert weights["AAA"] == pytest.approx(1.0)


def test_tsmom_cash_when_negative_return(synthetic_prices):
    """CCC has -0.0003/day drift, after 252 days r_252 < 0 → cash (weight 0)."""
    as_of = synthetic_prices.index[-1]
    weights = allocate_tsmom_signal(
        synthetic_prices[["CCC"]], pd.Timestamp(as_of), lookback_days=252,
    )
    assert weights["CCC"] == pytest.approx(0.0)


def test_tsmom_per_asset_independent_signals(synthetic_prices):
    """AAA up + BBB flat + CCC down → AAA long, BBB likely 0 or 1, CCC cash."""
    as_of = synthetic_prices.index[-1]
    weights = allocate_tsmom_signal(
        synthetic_prices, pd.Timestamp(as_of), lookback_days=252,
    )
    # AAA must be long (uptrend)
    assert weights["AAA"] > 0
    # CCC must be cash (downtrend)
    assert weights["CCC"] == pytest.approx(0.0)
    # Long weights sum to 1 (equal-weight among long), CCC excluded
    long_total = sum(w for w in weights.values() if w > 0)
    assert long_total == pytest.approx(1.0, abs=1e-9)
    # Each long asset gets equal weight
    n_long = sum(1 for w in weights.values() if w > 0)
    expected_w = 1.0 / n_long
    for w in weights.values():
        assert w == pytest.approx(0.0) or w == pytest.approx(expected_w)


def test_tsmom_all_cash_when_all_assets_negative():
    """3 assets all in downtrend → all cash."""
    dates = pd.date_range("2023-01-01", periods=300, freq="B")
    rng = np.random.default_rng(7)
    a = 100.0 * np.exp(np.cumsum(-0.001 + rng.normal(0, 0.005, 300)))
    b = 100.0 * np.exp(np.cumsum(-0.001 + rng.normal(0, 0.005, 300)))
    c = 100.0 * np.exp(np.cumsum(-0.001 + rng.normal(0, 0.005, 300)))
    prices = pd.DataFrame({"A": a, "B": b, "C": c}, index=dates)
    weights = allocate_tsmom_signal(
        prices, pd.Timestamp(dates[-1]), lookback_days=252,
    )
    assert sum(weights.values()) == pytest.approx(0.0)
    assert all(w == 0.0 for w in weights.values())


def test_tsmom_dispatcher_via_allocate_method(synthetic_prices):
    """PortfolioAllocator.allocate(method='tsmom') routes correctly."""
    alloc = PortfolioAllocator(["AAA", "BBB", "CCC"])
    as_of = synthetic_prices.index[-1]
    result = alloc.allocate(
        synthetic_prices, pd.Timestamp(as_of),
        method="tsmom", tsmom_lookback_days=252,
    )
    assert result.method == "tsmom"
    assert result.weights["AAA"] > 0
    assert result.weights["CCC"] == pytest.approx(0.0)
    # cash_weight + sum(weights) = 1
    assert sum(result.weights.values()) + result.cash_weight == pytest.approx(1.0, abs=1e-9)
