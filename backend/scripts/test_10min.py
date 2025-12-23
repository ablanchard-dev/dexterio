#!/usr/bin/env python3
"""Test ULTRA-COURT (10 minutes) pour valider les optimisations"""
import sys
import time
import logging
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

# Réduire logging
logging.getLogger('engines').setLevel(logging.ERROR)

from backtest.engine import BacktestEngine
from models.backtest import BacktestConfig

# Test 10 MINUTES (09:30-09:40)
config = BacktestConfig(
    run_name='ultra_fast_10min',
    start_date=datetime(2024, 6, 12, 9, 30, 0),
    end_date=datetime(2024, 6, 12, 9, 40, 0),
    symbols=['SPY'],
    data_paths=['/app/data/historical/1m/SPY.parquet'],
    initial_capital=10000.0,
    trading_mode='AGGRESSIVE',
    trade_types=['DAILY', 'SCALP']
)

print("Testing optimizations on 10 minutes...")
t0 = time.time()
engine = BacktestEngine(config)
engine.load_data()
result = engine.run()
elapsed = time.time() - t0

print(f"\n✅ 10 minutes completed in {elapsed:.2f}s")
print(f"Speed: {elapsed/10*60:.1f}s per hour")
print(f"Estimated 1 day (6.5h): {elapsed/10*390:.1f}s = {elapsed/10*390/60:.1f}min")
print(f"\nTrades: {result.total_trades}, Total R: {result.total_r:+.2f}R")

if elapsed / 10 * 390 <= 900:  # 1 jour en ≤ 15min
    print(f"\n🎯 TARGET MET: 1 day should complete in ≤ 15 minutes")
else:
    print(f"\n⚠️  Still too slow: {elapsed/10*390/60:.1f}min for 1 day")
