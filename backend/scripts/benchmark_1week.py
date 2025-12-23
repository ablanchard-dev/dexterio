#!/usr/bin/env python3
"""
BENCHMARK COMPLET - 1 SEMAINE (5 jours marché)
Pipeline complet : agg → market_state → playbooks → execution
"""
import sys
import time
import json
from pathlib import Path
from datetime import datetime
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
logging.basicConfig(level=logging.WARNING)

from backtest.engine import BacktestEngine
from models.backtest import BacktestConfig

print("="*80)
print("BENCHMARK COMPLET - 1 SEMAINE")
print("="*80)

# 1 semaine de trading (5 jours)
config = BacktestConfig(
    run_name='benchmark_1week',
    start_date=datetime(2024, 6, 3, 9, 30, 0),
    end_date=datetime(2024, 6, 7, 16, 0, 0),
    symbols=['SPY', 'QQQ'],  # Les 2 symboles
    data_paths=[
        '/app/data/historical/1m/SPY.parquet',
        '/app/data/historical/1m/QQQ.parquet'
    ],
    initial_capital=10000.0,
    trading_mode='AGGRESSIVE',
    trade_types=['DAILY', 'SCALP']
)

print("\nLoading data...")
t_load = time.time()
engine = BacktestEngine(config)
engine.load_data()
t_load_elapsed = time.time() - t_load

spy_candles = len(engine.candles_1m_by_timestamp.get('SPY', {}))
qqq_candles = len(engine.candles_1m_by_timestamp.get('QQQ', {}))

print(f"Load: {t_load_elapsed:.2f}s")
print(f"SPY candles: {spy_candles}")
print(f"QQQ candles: {qqq_candles}")

# Activer instrumentation
engine.market_state_engine._instrumentation_log = []

# Tracking détaillé
bar_timings = []
market_state_calls_detail = []
playbook_calls = 0
pattern_calls = 0

print("\nRunning 1 week backtest...")
print("(This will call the REAL run() with full pipeline)")

t_run_start = time.time()

# Hook pour tracer les appels (monkey patch temporaire)
original_generate_setups = engine.setup_engine.generate_setups

def traced_generate_setups(*args, **kwargs):
    global playbook_calls
    playbook_calls += 1
    return original_generate_setups(*args, **kwargs)

engine.setup_engine.generate_setups = traced_generate_setups

# RUN COMPLET
result = engine.run()

t_run_elapsed = time.time() - t_run_start

print(f"\n{'='*80}")
print(f"BENCHMARK RESULTS - 1 WEEK")
print(f"{'='*80}")
print(f"Run time: {t_run_elapsed:.2f}s = {t_run_elapsed/60:.1f} minutes")
print(f"Bars processed: {result.bars_processed}")
print(f"ms/bar (avg): {t_run_elapsed/result.bars_processed*1000:.1f}ms")

# Stats de trading
print(f"\n📊 TRADING STATS")
print(f"Trades: {result.total_trades}")
print(f"Total R: {result.total_r:+.2f}R")
print(f"Win rate: {result.win_rate:.1f}%")
print(f"Profit factor: {result.profit_factor:.2f}")

# Instrumentation create_market_state
instrumentation = engine.market_state_engine._instrumentation_log

print(f"\n{'='*80}")
print(f"CREATE_MARKET_STATE ANALYSIS")
print(f"{'='*80}")
print(f"Total calls: {len(instrumentation)}")
print(f"Cache hit rate: {(1 - len(instrumentation)/result.bars_processed)*100:.1f}%")

if len(instrumentation) > 0:
    # Breakdown
    t_detect = [i['t_detect_structure_ms'] for i in instrumentation]
    t_bias = [i['t_bias_calc_ms'] for i in instrumentation]
    t_profile = [i['t_profile_confluence_ms'] for i in instrumentation]
    t_total = [i['t_total_ms'] for i in instrumentation]
    
    print(f"\nBreakdown (moyenne / P95 / P99):")
    print(f"  detect_structure: {np.mean(t_detect):.2f}ms / {np.percentile(t_detect, 95):.2f}ms / {np.percentile(t_detect, 99):.2f}ms")
    print(f"  bias_calc: {np.mean(t_bias):.2f}ms / {np.percentile(t_bias, 95):.2f}ms / {np.percentile(t_bias, 99):.2f}ms")
    print(f"  profile: {np.mean(t_profile):.2f}ms / {np.percentile(t_profile, 95):.2f}ms / {np.percentile(t_profile, 99):.2f}ms")
    print(f"  TOTAL: {np.mean(t_total):.2f}ms / {np.percentile(t_total, 95):.2f}ms / {np.percentile(t_total, 99):.2f}ms")
    
    # Candles HTF counts
    daily_counts = [i['daily_candles'] for i in instrumentation]
    h4_counts = [i['h4_candles'] for i in instrumentation]
    h1_counts = [i['h1_candles'] for i in instrumentation]
    
    print(f"\nCandles HTF (avg / min / max):")
    print(f"  Daily: {np.mean(daily_counts):.1f} / {np.min(daily_counts)} / {np.max(daily_counts)}")
    print(f"  4H: {np.mean(h4_counts):.1f} / {np.min(h4_counts)} / {np.max(h4_counts)}")
    print(f"  1H: {np.mean(h1_counts):.1f} / {np.min(h1_counts)} / {np.max(h1_counts)}")
    
    # Log détail des 5 premiers appels
    print(f"\nDETAIL DES 5 PREMIERS APPELS:")
    for i, entry in enumerate(instrumentation[:5], 1):
        print(f"  Call {i}: daily={entry['daily_candles']}, h4={entry['h4_candles']}, h1={entry['h1_candles']}, " +
              f"total={entry['t_total_ms']:.2f}ms (detect={entry['t_detect_structure_ms']:.2f}ms)")

print(f"\n{'='*80}")
print(f"PIPELINE ACTIVITY")
print(f"{'='*80}")
print(f"Playbook evaluations: {playbook_calls}")
print(f"Playbook calls per bar: {playbook_calls/result.bars_processed:.2f}")
print(f"Anti-spam blocks (cooldown): {engine.blocked_by_cooldown}")
print(f"Anti-spam blocks (session): {engine.blocked_by_session_limit}")

# Cache stats
cache_stats = engine.market_state_cache.get_stats()
print(f"\nCache stats:")
print(f"  Hits: {cache_stats['hits']}")
print(f"  Misses: {cache_stats['misses']}")
print(f"  Hit rate: {cache_stats['hit_rate']:.1f}%")

# Temps par composant (estimation)
total_time_ms = t_run_elapsed * 1000
time_in_market_state = sum(t_total) if instrumentation else 0
pct_market_state = time_in_market_state / total_time_ms * 100 if total_time_ms > 0 else 0

print(f"\n{'='*80}")
print(f"RÉPARTITION DU TEMPS")
print(f"{'='*80}")
print(f"Total run: {total_time_ms:.0f}ms")
print(f"Time in create_market_state: {time_in_market_state:.0f}ms ({pct_market_state:.1f}%)")
print(f"Time in other code: {total_time_ms - time_in_market_state:.0f}ms ({100-pct_market_state:.1f}%)")

# Extrapolation
bars_per_day = result.bars_processed / 5  # 5 jours
ms_per_bar = t_run_elapsed / result.bars_processed * 1000

print(f"\n{'='*80}")
print(f"EXTRAPOLATION")
print(f"{'='*80}")
print(f"Bars per day (avg): {bars_per_day:.0f}")
print(f"ms/bar: {ms_per_bar:.2f}ms")
print(f"1 day: {ms_per_bar * bars_per_day / 1000:.1f}s")
print(f"1 month (20 jours): {ms_per_bar * bars_per_day * 20 / 1000:.1f}s = {ms_per_bar * bars_per_day * 20 / 60000:.1f} minutes")
print(f"6 months (120 jours): {ms_per_bar * bars_per_day * 120 / 1000:.1f}s = {ms_per_bar * bars_per_day * 120 / 60000:.1f} minutes")

target_1day_sec = 900  # 15 min
actual_1day_sec = ms_per_bar * bars_per_day / 1000

if actual_1day_sec <= target_1day_sec:
    print(f"\n✅ TARGET MET: 1 day = {actual_1day_sec:.1f}s < 15min")
else:
    print(f"\n⚠️  Need {actual_1day_sec/target_1day_sec:.1f}x speedup")

# Save JSON
summary = {
    'bars_processed': result.bars_processed,
    'run_time_sec': t_run_elapsed,
    'ms_per_bar': ms_per_bar,
    'create_market_state_calls': len(instrumentation),
    'cache_hit_rate': cache_stats['hit_rate'],
    'trades': result.total_trades,
    'total_r': result.total_r,
    'playbook_calls': playbook_calls,
    'htf_candles_avg': {
        'daily': float(np.mean(daily_counts)) if instrumentation else 0,
        'h4': float(np.mean(h4_counts)) if instrumentation else 0,
        'h1': float(np.mean(h1_counts)) if instrumentation else 0
    },
    'extrapolation_1day_sec': actual_1day_sec
}

with open('/tmp/benchmark_1week.json', 'w') as f:
    json.dump(summary, f, indent=2)

print(f"\n✅ Summary saved to /tmp/benchmark_1week.json")
print(f"\n{'='*80}")
