"""Unit tests for stat_arb pure helpers (Sprint 3, phase D1).

Covers zscore rolling ops, Engle-Granger cointegration, and beta-neutral
pair sizing. Per dossier §F: ≥15 unit tests.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from backend.engines.stat_arb.cointegration import (
    EG_CRITICAL_VALUES,
    adf_stat_no_const,
    engle_granger_test,
    ols_beta_alpha,
)
from backend.engines.stat_arb.sizing import PairSize, pair_sizing
from backend.engines.stat_arb.zscore import (
    compute_spread,
    rolling_beta,
    rolling_mean,
    rolling_std,
    rolling_zscore,
)


# ---------- rolling_mean ----------------------------------------------------

def test_rolling_mean_basic():
    x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    m = rolling_mean(x, 3)
    assert np.isnan(m[0]) and np.isnan(m[1])
    assert m[2] == pytest.approx(2.0)
    assert m[3] == pytest.approx(3.0)
    assert m[4] == pytest.approx(4.0)


def test_rolling_mean_window_larger_than_series():
    x = np.array([1.0, 2.0])
    m = rolling_mean(x, 5)
    assert np.all(np.isnan(m))


def test_rolling_mean_invalid_window():
    with pytest.raises(ValueError):
        rolling_mean(np.array([1.0, 2.0]), 0)


# ---------- rolling_std -----------------------------------------------------

def test_rolling_std_matches_numpy_ddof1():
    rng = np.random.default_rng(42)
    x = rng.standard_normal(50)
    w = 10
    out = rolling_std(x, w)
    for i in range(w - 1, len(x)):
        expected = x[i - w + 1 : i + 1].std(ddof=1)
        assert out[i] == pytest.approx(expected, rel=1e-12)


def test_rolling_std_rejects_window_lt_2():
    with pytest.raises(ValueError):
        rolling_std(np.arange(10.0), 1)


# ---------- rolling_beta ----------------------------------------------------

def test_rolling_beta_recovers_ground_truth():
    rng = np.random.default_rng(0)
    x = rng.standard_normal(200)
    true_beta = 1.7
    y = true_beta * x + rng.standard_normal(200) * 0.01
    b = rolling_beta(y, x, 60)
    # last beta should be very close to true_beta
    assert abs(b[-1] - true_beta) < 0.05


def test_rolling_beta_zero_variance_yields_nan():
    x = np.ones(20)
    y = np.arange(20.0)
    b = rolling_beta(y, x, 5)
    # x has zero variance in every window → all NaN after warmup
    assert np.all(np.isnan(b[4:]))


# ---------- compute_spread / rolling_zscore ---------------------------------

def test_compute_spread_shape_check():
    with pytest.raises(ValueError):
        compute_spread(np.arange(5.0), np.arange(4.0), np.arange(5.0))


def test_rolling_zscore_centers_and_scales():
    rng = np.random.default_rng(7)
    x = rng.standard_normal(500)
    z = rolling_zscore(x, 50)
    tail = z[~np.isnan(z)]
    # z should be roughly mean 0, std 1
    assert abs(tail.mean()) < 0.2
    assert abs(tail.std() - 1.0) < 0.2


def test_rolling_zscore_constant_series_is_nan():
    x = np.full(100, 3.14)
    z = rolling_zscore(x, 20)
    # rolling std == 0 → NaN after warmup
    assert np.all(np.isnan(z))


# ---------- OLS + ADF + Engle-Granger ---------------------------------------

def test_ols_recovers_known_slope():
    x = np.linspace(0, 10, 100)
    y = 2.5 + 1.3 * x  # deterministic
    alpha, beta = ols_beta_alpha(y, x)
    assert alpha == pytest.approx(2.5, abs=1e-10)
    assert beta == pytest.approx(1.3, abs=1e-10)


def test_engle_granger_cointegrated_series():
    """Two series sharing a stationary spread should be flagged cointegrated."""
    rng = np.random.default_rng(123)
    n = 500
    common = np.cumsum(rng.standard_normal(n))  # random walk
    noise = rng.standard_normal(n) * 0.2
    y = common + noise  # cointegrated with common
    x = common + rng.standard_normal(n) * 0.2
    is_coint, stat, beta = engle_granger_test(y, x, alpha=0.05, max_lag=1)
    assert is_coint, f"expected cointegration, got stat={stat:.3f}, beta={beta:.3f}"
    assert stat < EG_CRITICAL_VALUES[0.05]


def test_engle_granger_non_cointegrated_series():
    """Two independent random walks should NOT be flagged cointegrated."""
    rng = np.random.default_rng(999)
    n = 500
    y = np.cumsum(rng.standard_normal(n))
    x = np.cumsum(rng.standard_normal(n))
    is_coint, stat, _ = engle_granger_test(y, x, alpha=0.05, max_lag=1)
    assert not is_coint, f"unexpected cointegration, stat={stat:.3f}"


def test_adf_stat_stationary_residuals_rejects_unit_root():
    rng = np.random.default_rng(3)
    # AR(1) with small coefficient → strongly stationary
    n = 500
    r = np.zeros(n)
    for i in range(1, n):
        r[i] = 0.3 * r[i - 1] + rng.standard_normal()
    stat = adf_stat_no_const(r, max_lag=1)
    # stationary residuals should give a strongly negative stat
    assert stat < -3.0


# ---------- pair_sizing -----------------------------------------------------

def test_pair_sizing_long_direction_signs():
    size = pair_sizing(
        risk_dollars=100.0,
        price_y=500.0,
        price_x=400.0,
        beta=1.0,
        direction="long",
        stop_distance_r_dollars=10.0,
    )
    assert isinstance(size, PairSize)
    assert size.qty_y > 0 and size.qty_x < 0


def test_pair_sizing_short_direction_signs():
    size = pair_sizing(
        risk_dollars=100.0,
        price_y=500.0,
        price_x=400.0,
        beta=1.0,
        direction="short",
        stop_distance_r_dollars=10.0,
    )
    assert size.qty_y < 0 and size.qty_x > 0


def test_pair_sizing_beta_neutrality_approx():
    """Dollar exposure on leg x should approx equal beta * dollar exposure on leg y."""
    beta = 1.2
    price_y = 450.0
    price_x = 380.0
    size = pair_sizing(
        risk_dollars=1000.0,
        price_y=price_y,
        price_x=price_x,
        beta=beta,
        direction="long",
        stop_distance_r_dollars=5.0,
    )
    notional_y = abs(size.qty_y) * price_y
    notional_x = abs(size.qty_x) * price_x
    # round-to-int introduces small error; tolerance = one share of x
    assert abs(notional_x - beta * notional_y) <= price_x


def test_pair_sizing_rejects_negative_beta():
    with pytest.raises(ValueError):
        pair_sizing(100.0, 500.0, 400.0, -1.0, "long", 10.0)


def test_pair_sizing_rejects_bad_direction():
    with pytest.raises(ValueError):
        pair_sizing(100.0, 500.0, 400.0, 1.0, "flat", 10.0)  # type: ignore[arg-type]


def test_pair_sizing_minimum_one_share():
    size = pair_sizing(
        risk_dollars=1.0,
        price_y=500.0,
        price_x=400.0,
        beta=1.0,
        direction="long",
        stop_distance_r_dollars=1000.0,
    )
    assert abs(size.qty_y) >= 1 and abs(size.qty_x) >= 1
