"""Engle-Granger cointegration test (numpy-only).

Step 1: OLS regression y = alpha + beta*x + residuals.
Step 2: ADF test on residuals (no intercept, no trend — residuals are
mean-zero by construction from OLS with intercept).

Critical values (MacKinnon asymptotic, 1-sided, residual ADF for bivariate
Engle-Granger with constant):
  1%: -3.90
  5%: -3.34
  10%: -3.04
These are the "Case 2" constants for bivariate cointegration tests.

Returns (is_cointegrated, adf_stat, beta) so callers can log everything.
"""
from __future__ import annotations

from typing import Tuple

import numpy as np

EG_CRITICAL_VALUES = {0.01: -3.90, 0.05: -3.34, 0.10: -3.04}


def ols_beta_alpha(y: np.ndarray, x: np.ndarray) -> Tuple[float, float]:
    """Classic OLS with intercept; returns (alpha, beta)."""
    if y.shape != x.shape:
        raise ValueError(f"y and x shape mismatch: {y.shape} vs {x.shape}")
    if y.size < 2:
        raise ValueError(f"need at least 2 observations, got {y.size}")
    xm = x.mean()
    ym = y.mean()
    dx = x - xm
    denom = float((dx * dx).sum())
    if denom == 0.0:
        raise ValueError("x has zero variance")
    beta = float((dx * (y - ym)).sum()) / denom
    alpha = float(ym - beta * xm)
    return alpha, beta


def adf_stat_no_const(residuals: np.ndarray, max_lag: int = 1) -> float:
    """Augmented Dickey-Fuller test statistic on residuals.

    Model:  Δr_t = rho * r_{t-1} + sum_{i=1..max_lag} gamma_i * Δr_{t-i} + eps
    Test stat: rho_hat / se(rho_hat).
    """
    r = np.asarray(residuals, dtype=float)
    n = r.size
    if n < max_lag + 5:
        raise ValueError(f"series too short (n={n}) for max_lag={max_lag}")

    dr = np.diff(r)
    y = dr[max_lag:]
    cols = [r[max_lag:-1]]
    for i in range(1, max_lag + 1):
        cols.append(dr[max_lag - i : -i] if i > 0 else dr[max_lag:])
    X = np.column_stack(cols)
    XtX = X.T @ X
    try:
        XtX_inv = np.linalg.inv(XtX)
    except np.linalg.LinAlgError:
        return np.nan
    beta_hat = XtX_inv @ X.T @ y
    resid = y - X @ beta_hat
    dof = X.shape[0] - X.shape[1]
    if dof <= 0:
        return np.nan
    sigma2 = float(resid @ resid) / dof
    se_rho = float(np.sqrt(sigma2 * XtX_inv[0, 0]))
    if se_rho == 0.0:
        return np.nan
    return float(beta_hat[0] / se_rho)


def engle_granger_test(
    y: np.ndarray,
    x: np.ndarray,
    alpha: float = 0.05,
    max_lag: int = 1,
) -> Tuple[bool, float, float]:
    """Two-step Engle-Granger test.

    Returns (is_cointegrated, adf_stat, beta).
    Rejects null of no cointegration when adf_stat < critical value.
    """
    if alpha not in EG_CRITICAL_VALUES:
        raise ValueError(f"alpha must be one of {list(EG_CRITICAL_VALUES)}")
    _, beta = ols_beta_alpha(y, x)
    residuals = y - (y.mean() - beta * x.mean()) - beta * x
    stat = adf_stat_no_const(residuals, max_lag=max_lag)
    crit = EG_CRITICAL_VALUES[alpha]
    is_coint = (not np.isnan(stat)) and stat < crit
    return is_coint, stat, beta
