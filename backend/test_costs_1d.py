#!/usr/bin/env python3
"""Test PHASE B: Backtest with costs (1 day)"""

from models.backtest import BacktestConfig
from backtest.engine import BacktestEngine
from utils.path_resolver import historical_data_path

config = BacktestConfig(
    run_name='costs_test_1d',
    symbols=['SPY'],
    data_paths=[str(historical_data_path('1m', 'SPY.parquet'))],
    start_date='2025-08-01',
    end_date='2025-08-01',
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

print('🚀 Starting backtest 1d with costs...')
engine = BacktestEngine(config)
result = engine.run()

print('\n' + '='*60)
print('📊 RÉSULTATS BACKTEST 1 JOUR')
print('='*60)
print(f'  Trades: {result.total_trades}')
print(f'  Total R Gross: {result.total_pnl_gross_R:.3f}R')
print(f'  Total R Net:   {result.total_pnl_net_R:.3f}R')
print(f'  Total Costs:   ${result.total_costs_dollars:.2f}')
print(f'  Cost Impact:   {(result.total_pnl_gross_R - result.total_pnl_net_R):.3f}R')
print(f'  Win Rate:      {result.winrate:.1f}%')
print(f'  Profit Factor: {result.profit_factor:.2f}')
print('='*60)
