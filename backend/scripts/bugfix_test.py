#!/usr/bin/env python3
"""Test ULTRA-COURT pour valider le bugfix ExecutionEngine"""
import sys
import time
import logging
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

# Logs WARNING seulement
logging.basicConfig(level=logging.WARNING)
logging.getLogger('engines').setLevel(logging.ERROR)

from backtest.engine import BacktestEngine
from models.backtest import BacktestConfig

print("="*80)
print("BUGFIX VALIDATION - 5 minutes test")
print("="*80)

config = BacktestConfig(
    run_name='bugfix_test_5min',
    start_date=datetime(2024, 6, 12, 9, 30, 0),
    end_date=datetime(2024, 6, 12, 9, 35, 0),
    symbols=['SPY'],
    data_paths=['/app/data/historical/1m/SPY.parquet'],
    initial_capital=10000.0,
    trading_mode='AGGRESSIVE',
    trade_types=['DAILY', 'SCALP']
)

print("Loading data...")
t_start = time.time()
engine = BacktestEngine(config)
engine.load_data()
t_load = time.time() - t_start

print(f"Data loaded in {t_load:.2f}s")
print("Running backtest (5 minutes)...")

t_run_start = time.time()
try:
    result = engine.run()
    t_run = time.time() - t_run_start
    
    print(f"\n✅ BUGFIX VALIDATION PASSED")
    print(f"   Run completed without crash: {t_run:.2f}s")
    print(f"   Trades: {result.total_trades}")
    print(f"   Total R: {result.total_r:+.2f}R")
    print(f"   Cooldown blocks: {engine.blocked_by_cooldown}")
    print(f"   Session blocks: {engine.blocked_by_session_limit}")
    
    cache_stats = engine.market_state_cache.get_stats()
    print(f"\n💾 Cache Stats:")
    print(f"   Hit rate: {cache_stats['hit_rate']:.1f}%")
    
except Exception as e:
    print(f"\n❌ BUGFIX VALIDATION FAILED")
    print(f"   Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
