#!/usr/bin/env python3
"""Sanity Check: 5j + 1 mois validation avant 6 mois"""
import sys
sys.path.insert(0, '/app/backend')

import pandas as pd
from pathlib import Path
from models.backtest import BacktestConfig
from backtest.engine import BacktestEngine
import engines.risk_engine as risk_module
import json
from datetime import datetime

print("="*80)
print("SANITY CHECK - DexterioBOT_HF")
print("="*80)

# Load data
spy = pd.read_parquet('/app/data/historical/1m/SPY.parquet')
qqq = pd.read_parquet('/app/data/historical/1m/QQQ.parquet')

if isinstance(spy.index, pd.DatetimeIndex):
    spy['datetime'] = spy.index
if isinstance(qqq.index, pd.DatetimeIndex):
    qqq['datetime'] = qqq.index

spy['datetime'] = pd.to_datetime(spy['datetime'], utc=True)
qqq['datetime'] = pd.to_datetime(qqq['datetime'], utc=True)

test_windows = [
    {'name': '5_days', 'start': '2025-06-02', 'end': '2025-06-07'},
    {'name': '1_month', 'start': '2025-06-02', 'end': '2025-07-02'},
]

scenarios = [
    {
        'id': 'scalp_aplus',
        'mode': 'SAFE',
        'types': ['SCALP'],
        'allowlist_safe': ['SCALP_Aplus_1_Mini_FVG_Retest_NY_Open'],
    },
    {
        'id': 'multi_playbooks',
        'mode': 'AGGRESSIVE',
        'types': ['DAILY', 'SCALP'],
        'allowlist_agg': [],
        'denylist_agg': ['Morning_Trap_Reversal'],
    },
]

results = {}

for window in test_windows:
    print(f"\n{'='*80}")
    print(f"WINDOW: {window['name']} ({window['start']} → {window['end']})")
    print(f"{'='*80}")
    
    start = pd.Timestamp(window['start'], tz='UTC')
    end = pd.Timestamp(window['end'], tz='UTC')
    
    spy_w = spy[(spy['datetime'] >= start) & (spy['datetime'] < end)].copy()
    qqq_w = qqq[(qqq['datetime'] >= start) & (qqq['datetime'] < end)].copy()
    
    temp_dir = Path(f"/tmp/sanity_{window['name']}")
    temp_dir.mkdir(exist_ok=True)
    spy_w.to_parquet(temp_dir / 'SPY.parquet', index=False)
    qqq_w.to_parquet(temp_dir / 'QQQ.parquet', index=False)
    
    for scenario in scenarios:
        print(f"\n  Scenario: {scenario['id']} ({scenario['mode']})")
        
        # Set allowlist
        if scenario['mode'] == 'SAFE':
            risk_module.SAFE_ALLOWLIST = scenario['allowlist_safe']
            risk_module.AGGRESSIVE_ALLOWLIST = []
            risk_module.AGGRESSIVE_DENYLIST = []
        else:
            risk_module.AGGRESSIVE_ALLOWLIST = scenario.get('allowlist_agg', [])
            risk_module.AGGRESSIVE_DENYLIST = scenario.get('denylist_agg', [])
            risk_module.SAFE_ALLOWLIST = []
        
        config = BacktestConfig(
            trading_mode=scenario['mode'],
            trade_types=scenario['types'],
            symbols=['SPY', 'QQQ'],
            data_paths=[str(temp_dir / 'SPY.parquet'), str(temp_dir / 'QQQ.parquet')],
            initial_capital=100000.0,
            run_name=f"sanity_{window['name']}_{scenario['id']}",
            output_dir=f"/tmp/sanity_output/{window['name']}/{scenario['id']}"
        )
        
        engine = BacktestEngine(config)
        result = engine.run()
        
        # Extract skip counts (from logs if possible, else estimate)
        # For now, use trade count as proxy
        
        key = f"{window['name']}_{scenario['id']}"
        results[key] = {
            'window': window['name'],
            'scenario': scenario['id'],
            'mode': scenario['mode'],
            'trades': result.total_trades,
            'winrate': result.winrate,
            'total_r': result.total_pnl_r,
            'pf': result.profit_factor,
            'max_dd_r': result.max_drawdown_r,
            'expectancy_r': result.expectancy_r,
        }
        
        print(f"    Trades: {result.total_trades}")
        print(f"    WR: {result.winrate:.1f}%")
        print(f"    Total R: {result.total_pnl_r:+.2f}")
        print(f"    PF: {result.profit_factor:.2f}")
        print(f"    MaxDD: {result.max_drawdown_r:.2f}R")
        print(f"    Expectancy: {result.expectancy_r:+.3f}R")

# Save results
output_path = Path('/tmp/sanity_check_results.json')
with output_path.open('w') as f:
    json.dump(results, f, indent=2)

print(f"\n{'='*80}")
print("SANITY CHECK RESULTS")
print(f"{'='*80}")

# Verdict
pass_criteria = {
    '5_days': {'min_trades': 2, 'min_r': -2.0},
    '1_month': {'min_trades': 10, 'min_r': 0.0},
}

verdict = "OK"
for key, res in results.items():
    window_name = res['window']
    if window_name in pass_criteria:
        criteria = pass_criteria[window_name]
        if res['trades'] < criteria['min_trades']:
            print(f"⚠️ {key}: trades {res['trades']} < {criteria['min_trades']} (FAIL)")
            verdict = "NOT OK"
        if res['total_r'] < criteria['min_r']:
            print(f"⚠️ {key}: total_r {res['total_r']:.2f} < {criteria['min_r']:.2f} (FAIL)")
            verdict = "NOT OK"

print(f"\n{'='*80}")
print(f"VERDICT: {verdict}")
if verdict == "OK":
    print("✅ Prêt pour backtest 6 mois")
else:
    print("❌ Corrections nécessaires avant 6 mois")
print(f"{'='*80}")
print(f"Results saved: {output_path}")
