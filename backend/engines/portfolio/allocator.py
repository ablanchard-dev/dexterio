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

AllocationMethod = Literal["equal_weight", "momentum", "vol_target", "risk_parity"]


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
                elif ov not in ("vol_target",):
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
