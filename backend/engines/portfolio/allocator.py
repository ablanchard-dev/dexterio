"""F2 Portfolio allocator — multi-asset daily rebalance.

Post §0.3 point 3bis Outcome B pivot. Abandon ICT intraday per-trade model ;
replace by multi-asset daily allocation with academic-backed signals :
    - Vol-targeting (cible Y% annual vol)
    - Momentum (J&T 12-1 — 12 months minus 1 month)
    - Mean-rev VIX-regime overlay (fertile 15-25)
    - Risk-parity fallback when momentum signal ambiguous

Metrics : Sharpe daily + Martin ratio + max drawdown (no E[R] per-trade).
Rebalance : monthly (21 trading days).

Contract :
    PortfolioAllocator(tickers=["SPY",...]).allocate(prices_df, as_of, method="momentum")
        returns dict {ticker: weight} summing to ≤1 (cash = residual)

Pure function, no I/O. Input : pandas DataFrame with date index + close price
columns per ticker. Output : weights dict.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Literal, Optional, Sequence

import numpy as np
import pandas as pd

AllocationMethod = Literal["equal_weight", "momentum", "vol_target", "risk_parity", "tsmom"]


@dataclass(frozen=True)
class AllocationResult:
    """Frozen snapshot of one allocation decision."""

    as_of: pd.Timestamp
    method: str
    weights: Dict[str, float]  # ticker → weight in [0, 1], sum ≤ 1.0
    cash_weight: float  # 1 - sum(weights)
    diagnostic: Dict[str, float] = field(default_factory=dict)


def allocate_equal_weight(tickers: Sequence[str]) -> Dict[str, float]:
    """Equal weight across all tickers. Cash residual = 0."""
    w = 1.0 / len(tickers)
    return {t: w for t in tickers}


def allocate_momentum_jt(
    prices: pd.DataFrame,
    as_of: pd.Timestamp,
    lookback_months: int = 12,
    skip_months: int = 1,
    top_n: int = 3,
) -> Dict[str, float]:
    """Jegadeesh-Titman 12-1 momentum : rank tickers by return over
    (as_of - lookback_months) to (as_of - skip_months). Long top N equal-weight.

    Args:
        prices : date-indexed df, columns = tickers, values = close prices.
        as_of : allocation decision date.
        lookback_months : total lookback window (default 12).
        skip_months : recent months to exclude (default 1 — J&T 12-1).
        top_n : number of winners to hold long (equal weight each).
    """
    if prices.empty:
        return {}
    start = as_of - pd.DateOffset(months=lookback_months)
    end = as_of - pd.DateOffset(months=skip_months)
    window = prices.loc[start:end]
    if len(window) < 10:
        return {t: 0.0 for t in prices.columns}
    ret = window.iloc[-1] / window.iloc[0] - 1.0
    ranked = ret.sort_values(ascending=False)
    winners = ranked.head(top_n).index.tolist()
    w = 1.0 / top_n
    weights = {t: 0.0 for t in prices.columns}
    for t in winners:
        weights[t] = w
    return weights


def allocate_vol_target(
    prices: pd.DataFrame,
    as_of: pd.Timestamp,
    target_annual_vol: float = 0.12,
    vol_lookback_days: int = 60,
    base_weights: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    """Vol-targeting overlay : scale base_weights by target/realized vol.

    Uses the portfolio's realized volatility from the last `vol_lookback_days`
    and scales down (never up) to target. Caps total exposure at sum(base_weights).
    """
    if base_weights is None:
        base_weights = allocate_equal_weight(list(prices.columns))
    if prices.empty:
        return base_weights
    window = prices.loc[:as_of].tail(vol_lookback_days)
    if len(window) < 10:
        return base_weights
    returns = window.pct_change().dropna()
    tickers = list(base_weights.keys())
    w_vec = np.array([base_weights.get(t, 0.0) for t in tickers])
    cov = returns[tickers].cov()
    port_variance = float(w_vec @ cov.values @ w_vec)
    if port_variance <= 0:
        return base_weights
    port_vol_annual = np.sqrt(port_variance * 252)
    if port_vol_annual <= 0:
        return base_weights
    scale = min(1.0, target_annual_vol / port_vol_annual)
    return {t: float(base_weights.get(t, 0.0) * scale) for t in tickers}


def apply_vix_regime_overlay(
    weights: Dict[str, float],
    vix_series: pd.Series,
    as_of: pd.Timestamp,
    *,
    fertile_range: tuple = (15.0, 25.0),
    panic_threshold: float = 30.0,
    low_vol_threshold: float = 13.0,
    scale_outside_fertile: float = 0.5,
    scale_panic: float = 0.0,
) -> Dict[str, float]:
    """VIX regime overlay (§0.4-bis fertile 15-25).

    - VIX in fertile range [15, 25] → keep weights as-is (full risk-on)
    - VIX < low_vol_threshold (e.g. <13) → scale down (too complacent, reversal risk)
    - VIX >= panic_threshold (>=30) → scale to 0 (deleverage)
    - VIX 25-30 → proportional scale down (linear interpolation)

    Reads VIX prior-day close (lookup as_of index in vix_series, one-day lag
    to avoid lookahead).
    """
    if vix_series.empty:
        return weights
    try:
        # Use prior day's VIX (merge_asof style)
        vix_idx = vix_series.index.get_indexer([as_of], method="pad")[0]
        if vix_idx < 0:
            return weights
        vix_now = float(vix_series.iloc[vix_idx])
    except (KeyError, IndexError):
        return weights
    if pd.isna(vix_now):
        return weights

    lo, hi = fertile_range
    if lo <= vix_now <= hi:
        scale = 1.0  # fertile — full exposure
    elif vix_now < low_vol_threshold:
        scale = scale_outside_fertile  # low vol — reduce (reversal risk)
    elif vix_now >= panic_threshold:
        scale = scale_panic  # panic — deleverage
    elif hi < vix_now < panic_threshold:
        # Linear interpolation between hi (scale=1) and panic (scale=0).
        span = panic_threshold - hi
        t = (vix_now - hi) / span
        scale = 1.0 - t
    else:
        # Between low_vol_threshold and lo : interpolate
        span = lo - low_vol_threshold
        t = (vix_now - low_vol_threshold) / span if span > 0 else 1.0
        scale = scale_outside_fertile + t * (1.0 - scale_outside_fertile)

    return {t: float(w * scale) for t, w in weights.items()}


def allocate_tsmom_signal(
    prices: pd.DataFrame,
    as_of: pd.Timestamp,
    lookback_days: int = 252,
    tickers: Optional[Sequence[str]] = None,
) -> Dict[str, float]:
    """Time-Series Momentum per-asset (Moskowitz/Ooi/Pedersen 2012).

    For each asset independently : long if r_{lookback_days} > 0, cash otherwise.
    Long-positioned assets share equal weight (1/n_long).

    DIFFERS from allocate_momentum_jt (cross-sectional top-N picks). TSMOM is
    PER-ASSET absolute return persistence (signal = sign of own return), not
    relative ranking across the universe. Each asset's inclusion is independent.

    Academic reference : Moskowitz/Ooi/Pedersen (2012) "Time Series Momentum",
    Journal of Financial Economics. 12-month lookback canonical.

    Args:
        prices : date-indexed df, columns = tickers, values = close prices.
        as_of : allocation decision date.
        lookback_days : trading-day lookback (default 252 ≈ 12 months).
        tickers : optional subset of prices.columns ; defaults to all columns.

    Returns:
        Dict ticker → weight. Long assets = 1/n_long each, others 0. If 0 long,
        all weights = 0 (full cash).
    """
    if tickers is None:
        tickers = list(prices.columns)
    if prices.empty:
        return {t: 0.0 for t in tickers}
    window = prices.loc[:as_of].tail(lookback_days + 1)
    if len(window) < 10:
        return {t: 0.0 for t in tickers}
    long_assets = []
    for t in tickers:
        if t not in window.columns:
            continue
        col = window[t].dropna()
        if len(col) < 10:
            continue
        ret = col.iloc[-1] / col.iloc[0] - 1.0
        if ret > 0:
            long_assets.append(t)
    if not long_assets:
        return {t: 0.0 for t in tickers}
    w = 1.0 / len(long_assets)
    return {t: (w if t in long_assets else 0.0) for t in tickers}


def allocate_risk_parity(
    prices: pd.DataFrame,
    as_of: pd.Timestamp,
    vol_lookback_days: int = 60,
    tickers: Optional[Sequence[str]] = None,
) -> Dict[str, float]:
    """Simple inverse-volatility risk parity : w_i ∝ 1 / σ_i.

    Doesn't solve full Markowitz ; approximates risk-parity via inverse vol
    which is standard for low-N portfolios (N ≤ 10 ETFs).
    """
    if tickers is None:
        tickers = list(prices.columns)
    window = prices.loc[:as_of].tail(vol_lookback_days)
    if len(window) < 10:
        return allocate_equal_weight(tickers)
    vols = window[tickers].pct_change().std()
    inv_vol = 1.0 / vols.replace(0, np.nan)
    inv_vol = inv_vol.dropna()
    if inv_vol.empty:
        return allocate_equal_weight(tickers)
    w = inv_vol / inv_vol.sum()
    return {t: float(w.get(t, 0.0)) for t in tickers}


class PortfolioAllocator:
    """Composable allocator with multiple methods + overlays.

    Typical flow :
        alloc = PortfolioAllocator(tickers=["SPY","QQQ",...])
        for rebalance_date in schedule:
            result = alloc.allocate(prices, as_of=rebalance_date,
                                     method="momentum",
                                     overlays=["vol_target"])
    """

    def __init__(self, tickers: Sequence[str]) -> None:
        self._tickers = list(tickers)

    @property
    def tickers(self) -> List[str]:
        return list(self._tickers)

    def allocate(
        self,
        prices: pd.DataFrame,
        as_of: pd.Timestamp,
        *,
        method: AllocationMethod = "equal_weight",
        overlays: Optional[Sequence[str]] = None,
        target_annual_vol: float = 0.12,
        jt_lookback: int = 12,
        jt_skip: int = 1,
        jt_top_n: int = 3,
        tsmom_lookback_days: int = 252,
        vix_series: Optional[pd.Series] = None,
    ) -> AllocationResult:
        """Run the chosen allocation method + optional overlays (vol_target)."""
        if method == "equal_weight":
            weights = allocate_equal_weight(self._tickers)
        elif method == "momentum":
            weights = allocate_momentum_jt(
                prices[self._tickers], as_of,
                lookback_months=jt_lookback,
                skip_months=jt_skip,
                top_n=jt_top_n,
            )
        elif method == "risk_parity":
            weights = allocate_risk_parity(
                prices[self._tickers], as_of,
            )
        elif method == "tsmom":
            weights = allocate_tsmom_signal(
                prices[self._tickers], as_of,
                lookback_days=tsmom_lookback_days,
                tickers=self._tickers,
            )
        elif method == "vol_target":
            # Pure vol_target on equal-weight base
            base = allocate_equal_weight(self._tickers)
            weights = allocate_vol_target(
                prices[self._tickers], as_of,
                target_annual_vol=target_annual_vol,
                base_weights=base,
            )
        else:
            raise ValueError(f"Unknown method: {method!r}")

        # Overlays applied after base allocation.
        if overlays:
            for ov in overlays:
                if ov == "vol_target" and method != "vol_target":
                    weights = allocate_vol_target(
                        prices[self._tickers], as_of,
                        target_annual_vol=target_annual_vol,
                        base_weights=weights,
                    )
                elif ov == "vix_regime":
                    if vix_series is None:
                        raise ValueError(
                            "vix_regime overlay requires vix_series kwarg"
                        )
                    weights = apply_vix_regime_overlay(
                        weights, vix_series, as_of,
                    )
                elif ov not in ("vol_target", "vix_regime"):
                    raise ValueError(f"Unknown overlay: {ov!r}")

        total = sum(weights.values())
        cash = max(0.0, 1.0 - total)
        return AllocationResult(
            as_of=pd.Timestamp(as_of),
            method=method,
            weights=weights,
            cash_weight=cash,
            diagnostic={"total_invested": total},
        )
