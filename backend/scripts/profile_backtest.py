#!/usr/bin/env python3
"""Profiling du backtest pour identifier les goulots"""
import sys
import cProfile
import pstats
import io
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from backtest.engine import BacktestEngine
from models.backtest import BacktestConfig

def profile_backtest():
    # Test ultra-court : 30 minutes (09:30-10:00)
    config = BacktestConfig(
        run_name='profile_test',
        start_date=datetime(2024, 6, 12, 9, 30, 0),
        end_date=datetime(2024, 6, 12, 10, 0, 0),
        symbols=['SPY'],
        data_paths=['/app/data/historical/1m/SPY.parquet'],
        initial_capital=10000.0,
        trading_mode='AGGRESSIVE',
        trade_types=['DAILY', 'SCALP']
    )
    
    engine = BacktestEngine(config)
    engine.load_data()
    result = engine.run()
    
    print(f"\nCompleted: {result.total_trades} trades, {result.total_r:.2f}R")
    return result

if __name__ == "__main__":
    profiler = cProfile.Profile()
    profiler.enable()
    
    result = profile_backtest()
    
    profiler.disable()
    
    # Générer stats
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
    ps.print_stats(20)  # Top 20
    
    print("\n" + "="*80)
    print("TOP 20 FUNCTIONS BY CUMULATIVE TIME")
    print("="*80)
    print(s.getvalue())
