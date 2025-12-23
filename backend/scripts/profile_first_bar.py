#!/usr/bin/env python3
"""Profile PREMIÈRE BAR seulement"""
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

config = BacktestConfig(
    run_name='first_bar',
    start_date=datetime(2024, 6, 12, 9, 30, 0),
    end_date=datetime(2024, 6, 12, 9, 31, 0),
    symbols=['SPY'],
    data_paths=['/app/data/historical/1m/SPY.parquet'],
    initial_capital=10000.0,
    trading_mode='AGGRESSIVE',
    trade_types=['DAILY', 'SCALP']
)

print("Loading...")
engine = BacktestEngine(config)
engine.load_data()

# Monkey patch run() pour s'arrêter après 1 bar
original_run = engine.run

def run_one_bar():
    # Copier le début de run()
    engine.equity_curve_r = [0.0]
    engine.equity_curve_dollars = [config.initial_capital]
    
    start_date = engine.combined_data["datetime"].min()
    end_date = engine.combined_data["datetime"].max()
    engine.equity_timestamps = [start_date]
    
    minutes = sorted(engine.combined_data["datetime"].unique())
    
    print(f"Processing FIRST BAR ONLY (out of {len(minutes)} total)...")
    
    current_time = minutes[0]
    
    # Traiter cette bar
    htf_events = {}
    for symbol in engine.config.symbols:
        candle_1m = engine.candles_1m_by_timestamp.get(symbol, {}).get(current_time)
        if candle_1m is None:
            continue
        events = engine.tf_aggregator.add_1m_candle(candle_1m)
        htf_events[symbol] = events
    
    candidate_setups = []
    for symbol in engine.config.symbols:
        events = htf_events.get(symbol, {})
        setup = engine._process_bar_optimized(symbol, current_time, events)
        if setup is not None:
            candidate_setups.append(setup)
    
    print(f"First bar processed, {len(candidate_setups)} setups")
    
    # Retourner un résultat minimal
    from models.backtest import BacktestResult
    return BacktestResult(
        run_name='first_bar',
        start_date=start_date,
        end_date=start_date,
        initial_capital=10000,
        final_capital=10000,
        total_trades=0,
        trades=[],
        equity_curve_r=[],
        equity_curve_dollars=[],
        equity_timestamps=[],
        bars_processed=1
    )

engine.run = run_one_bar

print("Profiling FIRST BAR...")
profiler = cProfile.Profile()
profiler.enable()

t0 = time.time()
result = engine.run()
elapsed = time.time() - t0

profiler.disable()

print(f"\n✅ First bar: {elapsed:.2f}s")

# Top 20
s = io.StringIO()
pstats.Stats(profiler, stream=s).sort_stats('cumulative').print_stats(20)
print("\nTOP 20 FUNCTIONS:")
print(s.getvalue())

with open('/tmp/profile_first_bar.txt', 'w') as f:
    pstats.Stats(profiler, stream=f).sort_stats('cumulative').print_stats(50)
print("\n✅ /tmp/profile_first_bar.txt")
