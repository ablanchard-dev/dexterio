"""F2 Portfolio daily backtester — reconstruct equity curve from weights over time.

Pure logic : given weights[date] and prices[date, ticker], compute daily
equity evolution with monthly rebalance. Metrics: Sharpe daily, Martin
ratio, max DD, CAGR, total return.

No slippage/commission modeling in v1 (honest baseline, compare strategy
vs buy-and-hold SPY). Post-Stage-1 robustness : add transaction costs
+ rebalance slippage (standard 10bps per turnover).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

from engines.portfolio.allocator import AllocationResult, PortfolioAllocator


@dataclass(frozen=True)
class BacktestMetrics:
    """Frozen snapshot of portfolio backtest performance."""

    n_days: int
    n_rebalances: int
    total_return: float  # e.g. 0.25 for +25%
    cagr: float
    sharpe_daily_annualized: float
    martin_ratio: float  # CAGR / ulcer_index
    max_drawdown: float  # negative value, e.g. -0.15
    volatility_annualized: float
    cash_avg: float


def compute_metrics(equity: pd.Series) -> BacktestMetrics:
    """Compute standard performance metrics from an equity curve (starts at 1.0)."""
    if len(equity) < 2:
        return BacktestMetrics(0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    returns = equity.pct_change().dropna()
    total_return = float(equity.iloc[-1] / equity.iloc[0] - 1.0)
    n_days = len(returns)
    years = n_days / 252.0
    cagr = (1.0 + total_return) ** (1.0 / years) - 1.0 if years > 0 else 0.0

    # Sharpe daily annualized (risk-free ≈ 0 for simplicity, reported gross).
    if returns.std() > 0:
        sharpe = float(returns.mean() / returns.std() * np.sqrt(252))
    else:
        sharpe = 0.0

    # Max drawdown.
    running_max = equity.expanding().max()
    drawdown = equity / running_max - 1.0
    max_dd = float(drawdown.min())

    # Martin ratio : CAGR / ulcer_index where UI = sqrt(mean(drawdown²)).
    ulcer = float(np.sqrt((drawdown ** 2).mean())) if len(drawdown) > 0 else 0.0
    martin = cagr / ulcer if ulcer > 0 else 0.0

    vol_annual = float(returns.std() * np.sqrt(252))

    return BacktestMetrics(
        n_days=n_days,
        n_rebalances=0,  # caller sets
        total_return=total_return,
        cagr=cagr,
        sharpe_daily_annualized=sharpe,
        martin_ratio=martin,
        max_drawdown=max_dd,
        volatility_annualized=vol_annual,
        cash_avg=0.0,  # caller sets
    )


def run_backtest(
    prices: pd.DataFrame,
    allocator: PortfolioAllocator,
    *,
    method: str = "momentum",
    overlays: Optional[Sequence[str]] = None,
    rebalance_freq_days: int = 21,
    warmup_days: int = 252,
    transaction_cost_bps: float = 0.0,
    **allocator_kwargs,
) -> tuple[pd.Series, BacktestMetrics, List[AllocationResult]]:
    """Run a rolling-rebalance backtest.

    prices : date-indexed df with ticker columns (close prices, unadjusted OK
             since we use percent changes ; prefer adjusted for corporate
             actions).
    allocator : PortfolioAllocator configured with the ticker universe.
    method : allocation method name.
    rebalance_freq_days : bars between rebalances (21 ≈ monthly).
    warmup_days : days of history required before 1st allocation (e.g. 252 for
                  JT 12-month lookback).

    Returns : (equity_series, metrics, allocation_history).
    Equity starts at 1.0 on the 1st rebalance date.
    """
    dates = prices.index
    if len(dates) < warmup_days + rebalance_freq_days:
        raise ValueError(f"Not enough data : {len(dates)} < {warmup_days + rebalance_freq_days}")

    start_idx = warmup_days
    rebalance_indices = list(range(start_idx, len(dates), rebalance_freq_days))
    allocation_history: List[AllocationResult] = []
    equity = pd.Series(1.0, index=dates)
    equity.iloc[:start_idx] = np.nan

    current_weights: Dict[str, float] = {}
    current_equity = 1.0
    cash_weights: List[float] = []
    total_turnover = 0.0
    tc_rate = transaction_cost_bps / 10000.0  # bps → decimal

    for i, idx in enumerate(range(start_idx, len(dates))):
        date = dates[idx]
        # Rebalance on scheduled dates.
        if idx in rebalance_indices:
            result = allocator.allocate(
                prices, as_of=pd.Timestamp(date),
                method=method, overlays=overlays,
                **allocator_kwargs,
            )
            new_weights = result.weights
            # Turnover-based transaction cost (slippage + commission).
            # Cost = Σ |new_w - old_w| × tc_rate, applied to equity.
            if tc_rate > 0 and current_weights:
                all_tickers = set(new_weights.keys()) | set(current_weights.keys())
                turnover = sum(
                    abs(new_weights.get(t, 0.0) - current_weights.get(t, 0.0))
                    for t in all_tickers
                )
                total_turnover += turnover
                current_equity *= (1.0 - turnover * tc_rate)
            current_weights = new_weights
            cash_weights.append(result.cash_weight)
            allocation_history.append(result)
        # Compute daily return from current weights.
        if idx == start_idx or current_weights == {}:
            equity.iloc[idx] = current_equity
            continue
        prev_date = dates[idx - 1]
        day_ret = 0.0
        for ticker, w in current_weights.items():
            if ticker not in prices.columns:
                continue
            p_today = prices.loc[date, ticker]
            p_prev = prices.loc[prev_date, ticker]
            if pd.isna(p_today) or pd.isna(p_prev) or p_prev <= 0:
                continue
            day_ret += w * (p_today / p_prev - 1.0)
        current_equity *= (1.0 + day_ret)
        equity.iloc[idx] = current_equity

    equity = equity.dropna()
    metrics = compute_metrics(equity)
    metrics = BacktestMetrics(
        n_days=metrics.n_days,
        n_rebalances=len(allocation_history),
        total_return=metrics.total_return,
        cagr=metrics.cagr,
        sharpe_daily_annualized=metrics.sharpe_daily_annualized,
        martin_ratio=metrics.martin_ratio,
        max_drawdown=metrics.max_drawdown,
        volatility_annualized=metrics.volatility_annualized,
        cash_avg=float(np.mean(cash_weights)) if cash_weights else 0.0,
    )
    return equity, metrics, allocation_history


def buy_and_hold(prices: pd.DataFrame, ticker: str = "SPY") -> pd.Series:
    """Reference : buy-and-hold equity curve for a single ticker."""
    p = prices[ticker].dropna()
    return p / p.iloc[0]
