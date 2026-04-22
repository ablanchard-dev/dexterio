"""Rolling z-score and beta utilities for pair spreads.

Pure functions — no state, no IO. Inputs are aligned numpy arrays of
log prices (or raw prices; caller decides). All functions return NaN for
positions where the rolling window is not yet filled.
"""
from __future__ import annotations

import numpy as np


def rolling_mean(x: np.ndarray, window: int) -> np.ndarray:
    """Rolling mean; first window-1 entries are NaN.

    A segment containing any NaN yields NaN for that position (matches
    rolling_std semantics, avoids cumsum NaN propagation past the first
    NaN in the series).
    """
    if window < 1:
        raise ValueError(f"window must be >= 1, got {window}")
    n = x.size
    out = np.full(n, np.nan, dtype=float)
    if n < window:
        return out
    for i in range(window - 1, n):
        segment = x[i - window + 1 : i + 1]
        if np.isnan(segment).any():
            continue
        out[i] = segment.mean()
    return out


def rolling_std(x: np.ndarray, window: int, ddof: int = 1) -> np.ndarray:
    """Sample rolling std (ddof=1). First window-1 entries are NaN."""
    if window < 2:
        raise ValueError(f"window must be >= 2, got {window}")
    n = x.size
    out = np.full(n, np.nan, dtype=float)
    if n < window:
        return out
    for i in range(window - 1, n):
        segment = x[i - window + 1 : i + 1]
        out[i] = segment.std(ddof=ddof)
    return out


def rolling_beta(y: np.ndarray, x: np.ndarray, window: int) -> np.ndarray:
    """Rolling OLS beta from regression y = alpha + beta*x + eps.

    Returns beta_t for each t where the window [t-window+1, t] is full.
    First window-1 entries are NaN. No intercept returned (kept internal).
    """
    if y.shape != x.shape:
        raise ValueError(f"y and x shape mismatch: {y.shape} vs {x.shape}")
    if window < 2:
        raise ValueError(f"window must be >= 2, got {window}")
    n = y.size
    out = np.full(n, np.nan, dtype=float)
    if n < window:
        return out
    for i in range(window - 1, n):
        xi = x[i - window + 1 : i + 1]
        yi = y[i - window + 1 : i + 1]
        xm = xi.mean()
        ym = yi.mean()
        dx = xi - xm
        denom = float((dx * dx).sum())
        if denom == 0.0:
            out[i] = np.nan
        else:
            out[i] = float((dx * (yi - ym)).sum()) / denom
    return out


def compute_spread(
    log_y: np.ndarray, log_x: np.ndarray, beta: np.ndarray
) -> np.ndarray:
    """spread_t = log_y_t - beta_t * log_x_t. NaN propagates through beta."""
    if log_y.shape != log_x.shape or log_y.shape != beta.shape:
        raise ValueError("shape mismatch between log_y, log_x, beta")
    return log_y - beta * log_x


def rolling_zscore(spread: np.ndarray, window: int) -> np.ndarray:
    """z_t = (spread_t - rolling_mean(spread, window)_t) / rolling_std_t.

    First window-1 entries are NaN. If rolling std == 0, returns NaN.
    """
    mu = rolling_mean(spread, window)
    sigma = rolling_std(spread, window)
    with np.errstate(invalid="ignore", divide="ignore"):
        z = (spread - mu) / sigma
    z = np.where(sigma == 0.0, np.nan, z)
    return z
