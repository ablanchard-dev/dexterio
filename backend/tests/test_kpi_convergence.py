"""
KPI convergence tests (engine/job/ladder).

Goal: enforce a single, locked definition for:
- expectancy_r = mean(r_multiple) including breakevens
- profit_factor = gross_profit_R / abs(gross_loss_R), BE excluded

These definitions live in backtest/metrics.py and must match BacktestEngine outputs
and parquet-derived ladder metrics.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from backtest.engine import BacktestEngine
from backtest.metrics import (
    expectancy_from_r_multiples,
    max_drawdown_from_pnl_r_accounts,
    profit_factor_from_r_multiples,
)
from models.backtest import BacktestConfig, TradeResult
from utils.mini_lab_trade_metrics_parquet import summarize_trades_parquet


def _trade(
    *,
    trade_id: str,
    r_multiple_net: float,
    pnl_net_dollars: float,
    risk_dollars: float,
    outcome: str,
) -> TradeResult:
    ts0 = datetime(2025, 11, 3, 14, 30, tzinfo=timezone.utc)
    ts1 = datetime(2025, 11, 3, 15, 0, tzinfo=timezone.utc)
    return TradeResult(
        trade_id=trade_id,
        timestamp_entry=ts0,
        timestamp_exit=ts1,
        duration_minutes=30.0,
        symbol="SPY",
        direction="LONG",
        trade_type="DAILY",
        playbook="TEST",
        quality="A",
        entry_price=100.0,
        exit_price=101.0,
        stop_loss=99.0,
        take_profit_1=102.0,
        position_size=1.0,
        risk_pct=0.02,
        risk_amount=risk_dollars,
        pnl_net_dollars=pnl_net_dollars,
        pnl_dollars=pnl_net_dollars,
        pnl_net_R=r_multiple_net,
        pnl_r=r_multiple_net,
        outcome=outcome,
        exit_reason="test",
    )


def test_backtest_engine_expectancy_and_pf_use_locked_defs_with_breakeven_and_variable_risk(tmp_path):
    """
    Regression guard: the engine used to compute expectancy from win/loss probabilities
    and PF in $.

    This test forces:
    - a breakeven trade (0R) which must be INCLUDED in expectancy
    - variable risk_dollars across trades, so PF in $ would differ from PF in R
    """
    cfg = BacktestConfig(
        data_paths=[],
        symbols=["SPY"],
        trading_mode="AGGRESSIVE",
        trade_types=["DAILY"],
        output_dir=str(tmp_path),
    )
    engine = BacktestEngine(cfg)

    # r_multiples = [ +1.0, -0.5, 0.0 ] => expectancy = 0.1666..., PF = 2.0
    # But in $ with variable risk, PF would differ:
    #   profit$ = 100, loss$ = 100 => PF$ = 1.0 (not canonical)
    engine.trades = [
        _trade(trade_id="t1", r_multiple_net=1.0, pnl_net_dollars=100.0, risk_dollars=100.0, outcome="win"),
        _trade(trade_id="t2", r_multiple_net=-0.5, pnl_net_dollars=-100.0, risk_dollars=200.0, outcome="loss"),
        _trade(trade_id="t3", r_multiple_net=0.0, pnl_net_dollars=0.0, risk_dollars=150.0, outcome="breakeven"),
    ]

    r_multiples = [t.pnl_net_R for t in engine.trades]
    expected_expectancy = expectancy_from_r_multiples(r_multiples)
    expected_pf = profit_factor_from_r_multiples(r_multiples)
    base_r_unit_dollars = float(engine.risk_engine.state.base_r_unit_dollars)
    expected_max_dd = max_drawdown_from_pnl_r_accounts([t.pnl_dollars / base_r_unit_dollars for t in engine.trades])

    res = engine._generate_result(
        start_date=datetime(2025, 11, 3, tzinfo=timezone.utc),
        end_date=datetime(2025, 11, 3, tzinfo=timezone.utc),
        total_bars=1,
    )

    assert abs(res.expectancy_r - expected_expectancy) < 1e-9
    assert res.profit_factor == expected_pf
    assert abs(res.max_drawdown_r - expected_max_dd) < 1e-9


def test_summarize_trades_parquet_includes_pf_and_matches_locked_defs(tmp_path):
    df = pd.DataFrame(
        [
            {"r_multiple": 1.0, "pnl_dollars": 100.0, "pnl_R_account": 0.1, "outcome": "win"},
            {"r_multiple": -0.5, "pnl_dollars": -100.0, "pnl_R_account": -0.1, "outcome": "loss"},
            {"r_multiple": 0.0, "pnl_dollars": 0.0, "pnl_R_account": 0.0, "outcome": "breakeven"},
        ]
    )
    p = tmp_path / "trades.parquet"
    df.to_parquet(p, index=False)

    rep = summarize_trades_parquet(p)
    assert rep is not None

    r_multiples = [1.0, -0.5, 0.0]
    assert abs(rep["expectancy_r"] - expectancy_from_r_multiples(r_multiples)) < 1e-9
    assert rep["profit_factor"] == profit_factor_from_r_multiples(r_multiples)
    assert rep["max_drawdown_r"] == max_drawdown_from_pnl_r_accounts([0.1, -0.1, 0.0])
    assert rep["gross_profit_r"] == 1.0
    assert rep["gross_loss_r"] == -0.5
    assert rep["wins"] == 1
    assert rep["losses"] == 1
    assert rep["breakevens"] == 1
