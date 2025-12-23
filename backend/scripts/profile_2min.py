#!/usr/bin/env python3
"""
Profiling CPU détaillé avec cProfile - 2 minutes de données
"""
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

print("="*80)
print("PROFILING CPU - 2 MINUTES")
print("="*80)

config = BacktestConfig(
    run_name='profile_2min',
    start_date=datetime(2024, 6, 12, 9, 30, 0),
    end_date=datetime(2024, 6, 12, 9, 32, 0),
    symbols=['SPY'],
    data_paths=['/app/data/historical/1m/SPY.parquet'],
    initial_capital=10000.0,
    trading_mode='AGGRESSIVE',
    trade_types=['DAILY', 'SCALP']
)

# Load data (hors profiling pour isoler le run)
print("Loading data...")
t_load_start = time.time()
engine = BacktestEngine(config)
engine.load_data()
t_load = time.time() - t_load_start
print(f"Data loaded: {t_load:.2f}s")

# Profile le run
print("Profiling run...")
profiler = cProfile.Profile()
profiler.enable()

t_run_start = time.time()
result = engine.run()
t_run = time.time() - t_run_start

profiler.disable()

# Stats
bars = 2
ms_per_bar = (t_run / bars) * 1000

print(f"\n{'='*80}")
print(f"PROFILING RESULTS - 2 MINUTES")
print(f"{'='*80}")
print(f"Run time: {t_run:.2f}s")
print(f"Bars: {bars}")
print(f"ms/bar: {ms_per_bar:.1f}ms")
print(f"Trades: {result.total_trades}")

# Top 20 par cumtime
s = io.StringIO()
ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
ps.print_stats(20)

print(f"\n{'='*80}")
print(f"TOP 20 FUNCTIONS BY CUMULATIVE TIME")
print(f"{'='*80}")
print(s.getvalue())

# Sauvegarder stats complètes
with open('/tmp/profile_2min_full.txt', 'w') as f:
    ps = pstats.Stats(profiler, stream=f).sort_stats('cumulative')
    ps.print_stats(100)

print(f"\n✅ Full stats saved to /tmp/profile_2min_full.txt")

# Recherche spécifique detect_structure
s2 = io.StringIO()
ps2 = pstats.Stats(profiler, stream=s2).sort_stats('cumulative')
ps2.print_stats('detect_structure')

print(f"\n{'='*80}")
print(f"DETECT_STRUCTURE BREAKDOWN")
print(f"{'='*80}")
detect_output = s2.getvalue()
if detect_output.strip():
    print(detect_output)
else:
    print("No detect_structure calls found")

# Recherche create_market_state
s3 = io.StringIO()
ps3 = pstats.Stats(profiler, stream=s3).sort_stats('cumulative')
ps3.print_stats('create_market_state')

print(f"\n{'='*80}")
print(f"CREATE_MARKET_STATE BREAKDOWN")
print(f"{'='*80}")
market_state_output = s3.getvalue()
if market_state_output.strip():
    print(market_state_output)
else:
    print("No create_market_state calls found")

# Cache stats
cache_stats = engine.market_state_cache.get_stats()
print(f"\n{'='*80}")
print(f"CACHE STATS")
print(f"{'='*80}")
print(f"Hits: {cache_stats['hits']}")
print(f"Misses: {cache_stats['misses']}")
print(f"Hit rate: {cache_stats['hit_rate']:.1f}%")
print(f"Total calls: {cache_stats['hits'] + cache_stats['misses']}")
