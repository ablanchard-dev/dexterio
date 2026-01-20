#!/usr/bin/env python3
"""Test PHASE B: Backtest with costs (5 days) + Generate proof artifacts"""

import json
from models.backtest import BacktestConfig
from backtest.engine import BacktestEngine
from utils.path_resolver import historical_data_path, results_path
import pandas as pd

# Run 5 days
config = BacktestConfig(
    run_name='costs_test_5d',
    symbols=['SPY'],
    data_paths=[str(historical_data_path('1m', 'SPY.parquet'))],
    start_date='2025-08-01',
    end_date='2025-08-07',
    trading_mode='AGGRESSIVE',
    trade_types=['DAILY'],
    htf_warmup_days=40,
    commission_model='ibkr_fixed',
    enable_reg_fees=True,
    slippage_model='pct',
    slippage_cost_pct=0.0005,
    spread_model='fixed_bps',
    spread_bps=2.0
)

print('🚀 Starting backtest 5d with costs...')
engine = BacktestEngine(config)
result = engine.run()

print('\n' + '='*60)
print('📊 RÉSULTATS BACKTEST 5 JOURS')
print('='*60)
print(f'  Trades: {result.total_trades}')
print(f'  Total R Gross: {result.total_pnl_gross_R:.3f}R')
print(f'  Total R Net:   {result.total_pnl_net_R:.3f}R')
print(f'  Total Costs:   ${result.total_costs_dollars:.2f}')
print(f'  Cost Impact:   {(result.total_pnl_gross_R - result.total_pnl_net_R):.3f}R')
print(f'  Avg Cost/Trade: ${result.total_costs_dollars / result.total_trades:.2f}')
print(f'  Win Rate:      {result.winrate:.1f}%')
print(f'  Profit Factor: {result.profit_factor:.2f}')
print('='*60)

# Generate sanity proof
proof = {
    "run": "costs_test_5d",
    "period": "2025-08-01 to 2025-08-07",
    "trades": result.total_trades,
    "metrics": {
        "total_R_gross": float(result.total_pnl_gross_R),
        "total_R_net": float(result.total_pnl_net_R),
        "total_costs_dollars": float(result.total_costs_dollars),
        "cost_impact_R": float(result.total_pnl_gross_R - result.total_pnl_net_R),
        "avg_cost_per_trade_dollars": float(result.total_costs_dollars / result.total_trades) if result.total_trades > 0 else 0.0
    },
    "sanity_checks": {
        "net_less_than_or_equal_gross": result.total_pnl_net_R <= result.total_pnl_gross_R,
        "costs_positive": result.total_costs_dollars >= 0,
        "costs_reasonable": result.total_costs_dollars < result.total_pnl_gross_dollars if result.total_pnl_gross_dollars > 0 else True
    }
}

# Save proof
proof_path = results_path("costs_sanity_proof.json")
with open(proof_path, 'w') as f:
    json.dump(proof, f, indent=2)

print(f'\n💾 Sanity proof saved: {proof_path}')

# Verify trades parquet has cost columns
trades_file = results_path(f"trades_{config.run_name}_{config.trading_mode}_DAILY.parquet")
if trades_file.exists():
    df = pd.read_parquet(trades_file)
    cost_cols = [c for c in df.columns if 'cost' in c.lower() or 'commission' in c.lower() or 'fee' in c.lower() or 'slippage' in c.lower() or 'spread' in c.lower()]
    print(f'\n📊 Cost columns in trades parquet: {len(cost_cols)}')
    for col in cost_cols:
        print(f'  - {col}')
