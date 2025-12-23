#!/usr/bin/env python3
"""Test MINIMAL - 2 minutes - juste valider bugfix ExecutionEngine"""
import sys
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
logging.basicConfig(level=logging.ERROR)  # MINIMAL logs

from backtest.engine import BacktestEngine
from models.backtest import BacktestConfig

print("BUGFIX TEST - 2 minutes MINIMAL")

config = BacktestConfig(
    run_name='minimal_2min',
    start_date=datetime(2024, 6, 12, 9, 30, 0),
    end_date=datetime(2024, 6, 12, 9, 32, 0),  # 2 minutes seulement
    symbols=['SPY'],  # 1 symbole
    data_paths=['/app/data/historical/1m/SPY.parquet'],
    initial_capital=10000.0,
    trading_mode='AGGRESSIVE',
    trade_types=['DAILY', 'SCALP']
)

t_start = time.time()
engine = BacktestEngine(config)
engine.load_data()
t_load = time.time() - t_start

print(f"Data loaded: {t_load:.1f}s")

t_run_start = time.time()
try:
    result = engine.run()
    t_run = time.time() - t_run_start
    
    print(f"\n✅ BUGFIX VALIDATED")
    print(f"   Run: {t_run:.1f}s")
    print(f"   Trades: {result.total_trades}")
    print(f"   R: {result.total_r:+.2f}")
    
except ValueError as e:
    if "not found" in str(e):
        print(f"\n❌ BUGFIX FAILED: {e}")
        sys.exit(1)
    raise
except Exception as e:
    print(f"\n❌ UNEXPECTED ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
