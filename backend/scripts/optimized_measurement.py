#!/usr/bin/env python3
"""OPTIMIZED TEST - Benchmark après optimisations"""
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
from utils.path_resolver import historical_data_path

def run_optimized_test():
    """Test optimisé sur 30 minutes (même que baseline)"""
    config = BacktestConfig(
        run_name='optimized_30min',
        start_date=datetime(2024, 6, 12, 9, 30, 0),
        end_date=datetime(2024, 6, 12, 10, 0, 0),
        symbols=['SPY'],
        data_paths=[str(historical_data_path('1m', 'SPY.parquet'))],
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
    print("Running OPTIMIZED (30 minutes with caching)...")
    
    t_run_start = time.time()
    result = engine.run()
    t_run = time.time() - t_run_start
    
    return result, t_load, t_run, engine

if __name__ == "__main__":
    print("="*80)
    print("OPTIMIZED MEASUREMENT (after incremental aggregation + caching)")
    print("="*80)
    
    result, t_load, t_run, engine = run_optimized_test()
    
    bars = 30  # 30 minutes
    total_time = t_load + t_run
    ms_per_bar = (t_run / bars) * 1000
    bars_per_sec = bars / t_run if t_run > 0 else 0
    
    print(f"\n{'='*80}")
    print("OPTIMIZED RESULTS")
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
        print(f"⚠️ Still need optimization: {est_1day_min:.1f} minutes")
    
    # Comparer avec baseline
    try:
        with open('/tmp/baseline_metrics.txt', 'r') as f:
            baseline = {}
            for line in f:
                key, value = line.strip().split('=')
                baseline[key] = float(value)
        
        baseline_ms = baseline['ms_per_bar']
        speedup = baseline_ms / ms_per_bar
        
        print(f"\n🚀 PERFORMANCE GAIN")
        print(f"Baseline: {baseline_ms:.1f}ms/bar")
        print(f"Optimized: {ms_per_bar:.1f}ms/bar")
        print(f"Speedup: {speedup:.2f}x")
        
        if speedup >= 8:
            print(f"✅ Target speedup (8x) achieved!")
        else:
            print(f"⚠️ Need {8/speedup:.1f}x more speedup to reach 8x target")
        
        # Vérifier que les résultats sont similaires
        baseline_trades = baseline.get('trades', 0)
        baseline_r = baseline.get('total_r', 0)
        
        if abs(result.total_trades - baseline_trades) <= 1 and abs(result.total_r - baseline_r) < 1.0:
            print(f"\n✅ VALIDATION: Results match baseline (trades: {result.total_trades} vs {baseline_trades:.0f}, R: {result.total_r:.2f} vs {baseline_r:.2f})")
        else:
            print(f"\n⚠️ VALIDATION: Results differ from baseline!")
            print(f"   Trades: {result.total_trades} vs {baseline_trades:.0f}")
            print(f"   Total R: {result.total_r:.2f} vs {baseline_r:.2f}")
    
    except FileNotFoundError:
        print(f"\n⚠️ No baseline found - run baseline_measurement.py first")
    
    # Save optimized metrics
    with open('/tmp/optimized_metrics.txt', 'w') as f:
        f.write(f"ms_per_bar={ms_per_bar}\n")
        f.write(f"bars_per_sec={bars_per_sec}\n")
        f.write(f"trades={result.total_trades}\n")
        f.write(f"total_r={result.total_r}\n")
        f.write(f"cache_hits={cache_stats['hits']}\n")
        f.write(f"cache_misses={cache_stats['misses']}\n")
        f.write(f"cache_hit_rate={cache_stats['hit_rate']}\n")
    
    print(f"\n✅ Optimized metrics saved to /tmp/optimized_metrics.txt")
