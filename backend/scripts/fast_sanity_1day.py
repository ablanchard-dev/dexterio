#!/usr/bin/env python3
"""Test rapide avec optimisations"""
import sys
import time
import logging
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

# Réduire le logging des engines pendant le run
logging.getLogger('engines.market_state').setLevel(logging.WARNING)
logging.getLogger('engines.liquidity').setLevel(logging.WARNING)
logging.getLogger('engines.patterns.candlesticks').setLevel(logging.WARNING)
logging.getLogger('engines.patterns.ict').setLevel(logging.WARNING)
logging.getLogger('engines.setup_engine_v2').setLevel(logging.WARNING)
logging.getLogger('engines.risk_engine').setLevel(logging.WARNING)

from backtest.engine import BacktestEngine
from models.backtest import BacktestConfig

# Test 1 JOUR (09:30-16:00 = 390 minutes)
config = BacktestConfig(
    run_name='fast_test_1day',
    start_date=datetime(2024, 6, 12, 9, 30, 0),
    end_date=datetime(2024, 6, 12, 16, 0, 0),
    symbols=['SPY'],  # 1 symbole pour aller vite
    data_paths=['/app/data/historical/1m/SPY.parquet'],
    initial_capital=10000.0,
    trading_mode='AGGRESSIVE',
    trade_types=['DAILY', 'SCALP']
)

print("="*80)
print("FAST SANITY CHECK - 1 DAY (optimisé)")
print("="*80)

t0 = time.time()
engine = BacktestEngine(config)
engine.load_data()
t_load = time.time() - t0

print(f"Data loaded in {t_load:.2f}s")
print("Running backtest...")

t0 = time.time()
result = engine.run()
t_run = time.time() - t0

print(f"\n{'='*80}")
print(f"RÉSULTATS (1 jour - SPY seulement)")
print(f"={'='*80}")
print(f"⏱️  Data Load: {t_load:.2f}s")
print(f"⏱️  Total Run: {t_run:.2f}s ({t_run/60:.1f} minutes)")
print(f"⏱️  Speed: {t_run / result.bars_processed * 1000:.1f}ms per bar")

print(f"\n📊 MÉTRIQUES")
print(f"   Trades: {result.total_trades}")
print(f"   Total R: {result.total_r:+.2f}R")
print(f"   PF: {result.profit_factor:.2f}")
print(f"   WR: {result.win_rate:.1f}%")
print(f"   Expectancy: {result.expectancy_r:.2f}R/trade")
print(f"   MaxDD: {result.max_drawdown_r:.2f}R")

print(f"\n🛡️  ANTI-SPAM")
print(f"   Blocked by cooldown: {engine.blocked_by_cooldown}")
print(f"   Blocked by session limit: {engine.blocked_by_session_limit}")

print(f"\n{'='*80}")
if t_run <= 900:  # 15 minutes
    print(f"✅ PASS: Run completed in {t_run/60:.1f} minutes (< 15 min)")
else:
    print(f"⚠️  FAIL: Run took {t_run/60:.1f} minutes (> 15 min)")
print(f"{'='*80}")
