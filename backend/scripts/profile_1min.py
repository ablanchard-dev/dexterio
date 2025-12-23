#!/usr/bin/env python3
"""Profiling CPU - 1 MINUTE SEULEMENT"""
import sys
import cProfile
import pstats
import io
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
logging.basicConfig(level=logging.ERROR)

from backtest.engine import BacktestEngine
from models.backtest import BacktestConfig

print("PROFILING - 1 MINUTE")

config = BacktestConfig(
    run_name='profile_1min',
    start_date=datetime(2024, 6, 12, 9, 30, 0),
    end_date=datetime(2024, 6, 12, 9, 31, 0),
    symbols=['SPY'],
    data_paths=['/app/data/historical/1m/SPY.parquet'],
    initial_capital=10000.0,
    trading_mode='AGGRESSIVE',
    trade_types=['DAILY', 'SCALP']
)

print("Loading...")
t_load = time.time()
engine = BacktestEngine(config)
engine.load_data()
print(f"Load: {time.time()-t_load:.1f}s")

print("Profiling...")
profiler = cProfile.Profile()
profiler.enable()

t_run = time.time()
result = engine.run()
elapsed = time.time() - t_run

profiler.disable()

print(f"Run: {elapsed:.1f}s")
print(f"ms/bar: {elapsed*1000:.0f}ms")

# Top 20
s = io.StringIO()
pstats.Stats(profiler, stream=s).sort_stats('cumulative').print_stats(20)
print("\nTOP 20:")
print(s.getvalue())

# Save full
with open('/tmp/profile_1min.txt', 'w') as f:
    pstats.Stats(profiler, stream=f).sort_stats('cumulative').print_stats(100)
print("\n✅ /tmp/profile_1min.txt")
