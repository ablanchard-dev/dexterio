#!/usr/bin/env python3
"""
BENCHMARK OPTIMISÉ - 10 minutes avec TimeframeAggregator + MarketStateCache
"""
import sys
import time
import logging
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

# Logs ERROR seulement (minimal pour perf)
logging.basicConfig(level=logging.ERROR)

from backtest.engine import BacktestEngine
from models.backtest import BacktestConfig

print("="*80)
print("BENCHMARK OPTIMISÉ - 10 minutes")
print("TimeframeAggregator + MarketStateCache ACTIFS")
print("="*80)

config = BacktestConfig(
    run_name='benchmark_optimized_10min',
    start_date=datetime(2024, 6, 12, 9, 30, 0),
    end_date=datetime(2024, 6, 12, 9, 40, 0),  # 10 minutes
    symbols=['SPY'],
    data_paths=['/app/data/historical/1m/SPY.parquet'],
    initial_capital=10000.0,
    trading_mode='AGGRESSIVE',
    trade_types=['DAILY', 'SCALP']
)

print("\nLoading data...")
t_load_start = time.time()
engine = BacktestEngine(config)
engine.load_data()
t_load = time.time() - t_load_start

print(f"Data loaded in {t_load:.2f}s")
print("Running backtest...")

t_run_start = time.time()
result = engine.run()
t_run = time.time() - t_run_start

bars = 10  # 10 minutes
total_time = t_load + t_run
ms_per_bar = (t_run / bars) * 1000
bars_per_sec = bars / t_run if t_run > 0 else 0

print(f"\n{'='*80}")
print("BENCHMARK RESULTS - OPTIMIZED")
print(f"{'='*80}")
print(f"Data load: {t_load:.2f}s")
print(f"Run time: {t_run:.2f}s")
print(f"Total: {total_time:.2f}s")
print(f"Bars: {bars}")
print(f"Bars/sec: {bars_per_sec:.3f}")
print(f"ms/bar: {ms_per_bar:.1f}ms")

print(f"\n📊 TRADES")
print(f"Total: {result.total_trades}")
print(f"Total R: {result.total_r:+.2f}R")
print(f"Win Rate: {result.win_rate:.1f}%")

print(f"\n🛡️ ANTI-SPAM")
print(f"Blocked by cooldown: {engine.blocked_by_cooldown}")
print(f"Blocked by session limit: {engine.blocked_by_session_limit}")

# Cache stats
cache_stats = engine.market_state_cache.get_stats()
print(f"\n💾 CACHE STATS")
print(f"Hits: {cache_stats['hits']}")
print(f"Misses: {cache_stats['misses']}")
print(f"Hit rate: {cache_stats['hit_rate']:.1f}%")

# Extrapolation
est_1day_sec = (ms_per_bar / 1000) * 390
est_1day_min = est_1day_sec / 60

print(f"\n📈 EXTRAPOLATION")
print(f"1 day (390 bars): {est_1day_sec:.0f}s = {est_1day_min:.1f} minutes")

if est_1day_min <= 15:
    print(f"✅ TARGET MET: 1 day < 15 minutes")
else:
    needed = est_1day_sec / 900
    print(f"⚠️ Need {needed:.1f}x more speedup for 15min target")

print(f"\n{'='*80}")
