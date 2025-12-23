#!/usr/bin/env python3
"""BASELINE - Profiling avant optimisation pour mesurer le gain"""
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

def run_baseline_test():
    """Test baseline sur 30 minutes (assez pour mesurer mais pas trop long)"""
    config = BacktestConfig(
        run_name='baseline_30min',
        start_date=datetime(2024, 6, 12, 9, 30, 0),
        end_date=datetime(2024, 6, 12, 10, 0, 0),
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
    print("Running BASELINE (30 minutes)...")
    
    t_run_start = time.time()
    result = engine.run()
    t_run = time.time() - t_run_start
    
    return result, t_load, t_run, engine

if __name__ == "__main__":
    print("="*80)
    print("BASELINE MEASUREMENT (before optimization)")
    print("="*80)
    
    result, t_load, t_run, engine = run_baseline_test()
    
    bars = 30  # 30 minutes
    total_time = t_load + t_run
    ms_per_bar = (t_run / bars) * 1000
    bars_per_sec = bars / t_run if t_run > 0 else 0
    
    print(f"\n{'='*80}")
    print("BASELINE RESULTS")
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
    
    # Extrapolation
    est_1day_sec = (ms_per_bar / 1000) * 390
    est_1day_min = est_1day_sec / 60
    
    print(f"\n📈 EXTRAPOLATION")
    print(f"1 day (390 bars): {est_1day_sec:.0f}s = {est_1day_min:.1f} minutes")
    
    target_gain = est_1day_sec / 900  # Target = 15 min = 900s
    print(f"Speedup needed for 15min target: {target_gain:.1f}x")
    
    # Save baseline pour comparaison
    with open('/tmp/baseline_metrics.txt', 'w') as f:
        f.write(f"ms_per_bar={ms_per_bar}\n")
        f.write(f"bars_per_sec={bars_per_sec}\n")
        f.write(f"trades={result.total_trades}\n")
        f.write(f"total_r={result.total_r}\n")
        f.write(f"cooldown_blocks={engine.blocked_by_cooldown}\n")
        f.write(f"session_blocks={engine.blocked_by_session_limit}\n")
    
    print(f"\n✅ Baseline saved to /tmp/baseline_metrics.txt")
