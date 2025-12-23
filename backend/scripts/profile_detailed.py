#!/usr/bin/env python3
"""Profiling cProfile détaillé sur 10 minutes (logique complète réactivée)"""
import sys
import cProfile
import pstats
import io
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

# Garder logs WARNING seulement
import logging
logging.basicConfig(level=logging.WARNING)

from backtest.engine import BacktestEngine
from models.backtest import BacktestConfig

def run_backtest_10min():
    """Test 10 minutes avec logique complète"""
    config = BacktestConfig(
        run_name='profile_full_logic',
        start_date=datetime(2024, 6, 12, 9, 30, 0),
        end_date=datetime(2024, 6, 12, 9, 40, 0),
        symbols=['SPY'],  # 1 symbole pour profiling clair
        data_paths=['/app/data/historical/1m/SPY.parquet'],
        initial_capital=10000.0,
        trading_mode='AGGRESSIVE',
        trade_types=['DAILY', 'SCALP']
    )
    
    t_start = time.time()
    engine = BacktestEngine(config)
    engine.load_data()
    result = engine.run()
    t_total = time.time() - t_start
    
    return result, t_total, engine

if __name__ == "__main__":
    print("="*80)
    print("PROFILING - 10 minutes (logique complète)")
    print("="*80)
    
    profiler = cProfile.Profile()
    profiler.enable()
    
    result, total_time, engine = run_backtest_10min()
    
    profiler.disable()
    
    # Métriques de base
    bars_processed = 10  # 10 minutes
    ms_per_bar = (total_time / bars_processed) * 1000
    bars_per_sec = bars_processed / total_time if total_time > 0 else 0
    
    print(f"\n{'='*80}")
    print(f"BENCHMARK RESULTS")
    print(f"{'='*80}")
    print(f"Total runtime: {total_time:.2f}s")
    print(f"Bars processed: {bars_processed}")
    print(f"Bars/sec: {bars_per_sec:.2f}")
    print(f"ms/bar: {ms_per_bar:.1f}ms")
    print(f"\nTrades: {result.total_trades}, Total R: {result.total_r:+.2f}R")
    print(f"Blocked by cooldown: {engine.blocked_by_cooldown}")
    print(f"Blocked by session limit: {engine.blocked_by_session_limit}")
    
    # Extrapolation
    est_1day = (ms_per_bar / 1000) * 390
    print(f"\n📊 EXTRAPOLATION")
    print(f"   1 day (390 bars): {est_1day:.1f}s = {est_1day/60:.1f} minutes")
    
    if est_1day <= 900:
        print(f"   ✅ Target met: 1 day < 15 minutes")
    else:
        needed_speedup = est_1day / 900
        print(f"   ❌ Need {needed_speedup:.1f}x speedup to reach 15min target")
    
    # Top 15 fonctions par cumulative time
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
    ps.print_stats(15)
    
    print(f"\n{'='*80}")
    print(f"TOP 15 FUNCTIONS BY CUMULATIVE TIME")
    print(f"{'='*80}")
    print(s.getvalue())
    
    # Sauvegarder stats complètes
    with open('/tmp/profile_stats.txt', 'w') as f:
        ps = pstats.Stats(profiler, stream=f).sort_stats('cumulative')
        ps.print_stats(50)
    print(f"\nFull stats saved to /tmp/profile_stats.txt")
