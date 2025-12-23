#!/usr/bin/env python3
"""Quick timing analysis pour identifier les goulots"""
import sys
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from backtest.engine import BacktestEngine
from models.backtest import BacktestConfig

# Monkey patch pour timer les fonctions clés
original_process_bar = BacktestEngine._process_bar
original_build_market_state = None
original_detect_patterns = None

timings = {
    'process_bar': [],
    'market_state': [],
    'ict_patterns': [],
    'candle_patterns': [],
    'liquidity': [],
    'setup_generation': [],
    'risk_filtering': []
}

def timed_process_bar(self, symbol, current_time):
    t0 = time.time()
    result = original_process_bar(self, symbol, current_time)
    timings['process_bar'].append(time.time() - t0)
    return result

BacktestEngine._process_bar = timed_process_bar

# Test ultra-court : 10 minutes seulement
config = BacktestConfig(
    run_name='timing_test',
    start_date=datetime(2024, 6, 12, 9, 30, 0),
    end_date=datetime(2024, 6, 12, 9, 40, 0),
    symbols=['SPY'],
    data_paths=['/app/data/historical/1m/SPY.parquet'],
    initial_capital=10000.0,
    trading_mode='AGGRESSIVE',
    trade_types=['DAILY', 'SCALP']
)

print("Loading data...")
t0 = time.time()
engine = BacktestEngine(config)
engine.load_data()
t_load = time.time() - t0

print(f"Data loaded in {t_load:.2f}s")
print("Running backtest (10 minutes)...")

t0 = time.time()
result = engine.run()
t_run = time.time() - t0

print(f"\n{'='*80}")
print(f"TIMING ANALYSIS (10 minutes of data)")
print(f"{'='*80}")
print(f"Data Load: {t_load:.2f}s")
print(f"Total Run: {t_run:.2f}s")
print(f"Speed: {t_run / 10:.2f}s per minute")
print(f"\nTrades: {result.total_trades}")
print(f"Total R: {result.total_r:.2f}R")

if timings['process_bar']:
    avg_process_bar = sum(timings['process_bar']) / len(timings['process_bar'])
    total_process_bar = sum(timings['process_bar'])
    print(f"\n_process_bar calls: {len(timings['process_bar'])}")
    print(f"  Total time: {total_process_bar:.2f}s ({total_process_bar/t_run*100:.1f}% of run)")
    print(f"  Avg per call: {avg_process_bar*1000:.1f}ms")
    print(f"  Estimated 1 day (390 bars): {avg_process_bar * 390:.1f}s = {avg_process_bar * 390 / 60:.1f}min")

print(f"\n{'='*80}")
print(f"BOTTLENECK: _process_bar appelé à chaque minute pour chaque symbole")
print(f"SOLUTION: Optimiser les patterns/market_state à l'intérieur de _process_bar")
print(f"{'='*80}")
