#!/usr/bin/env python3
"""
P05B - Run RÉEL avec create_market_state() + breakdown interne
500 bars PROCESSED (après warmup)
"""
import sys
import time
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
logging.basicConfig(level=logging.ERROR)

from backtest.engine import BacktestEngine
from models.backtest import BacktestConfig

print("="*80)
print("P05B - RUN RÉEL 500 BARS PROCESSED")
print("="*80)

config = BacktestConfig(
    run_name='p05b_real_flow',
    start_date=datetime(2024, 6, 2, 8, 0, 0),
    end_date=datetime(2024, 6, 12, 16, 0, 0),
    symbols=['SPY'],
    data_paths=['/app/data/historical/1m/SPY.parquet'],
    initial_capital=10000.0,
    trading_mode='AGGRESSIVE',
    trade_types=['DAILY', 'SCALP']
)

print("\nLoading data...")
t_load = time.time()
engine = BacktestEngine(config)
engine.load_data()
print(f"Load: {time.time()-t_load:.2f}s")

# ACTIVER instrumentation interne
engine.market_state_engine._instrumentation_log = []

# Run jusqu'à 500 bars processed
print("\nRunning until 500 bars processed...")

minutes = sorted(engine.combined_data["datetime"].unique())
bars_processed = 0
TARGET = 500
cache_miss_log = []

t_run_start = time.time()

for idx, current_time in enumerate(minutes):
    if bars_processed >= TARGET:
        break
    
    # Ajouter à l'agrégateur
    htf_events = {}
    for symbol in engine.config.symbols:
        candle_1m = engine.candles_1m_by_timestamp.get(symbol, {}).get(current_time)
        if candle_1m is None:
            continue
        events = engine.tf_aggregator.add_1m_candle(candle_1m)
        htf_events[symbol] = events
    
    # Check warmup
    candles_1m = engine.tf_aggregator.get_candles('SPY', '1m')
    candles_5m = engine.tf_aggregator.get_candles('SPY', '5m')
    candles_1h = engine.tf_aggregator.get_candles('SPY', '1h')
    
    if len(candles_1m) < 50 or len(candles_5m) < 5 or len(candles_1h) < 2:
        continue  # Skip warmup
    
    # APPEL RÉEL _process_bar_optimized (flow réel)
    for symbol in engine.config.symbols:
        events = htf_events.get(symbol, {})
        
        # Track cache miss AVANT l'appel
        cache_misses_before = len(engine.market_state_engine._instrumentation_log)
        
        setup = engine._process_bar_optimized(symbol, current_time, events)
        
        # Track cache miss APRÈS l'appel
        cache_misses_after = len(engine.market_state_engine._instrumentation_log)
        
        if cache_misses_after > cache_misses_before:
            # create_market_state a été appelé
            cache_miss_log.append({
                'bar_idx': bars_processed,
                'ts': current_time.isoformat(),
                'is_close_1h': events.get('is_close_1h', False),
                'is_close_4h': events.get('is_close_4h', False),
                'is_close_1d': events.get('is_close_1d', False)
            })
    
    bars_processed += 1
    
    if bars_processed % 100 == 0:
        print(f"  {bars_processed}/{TARGET} bars processed...")

t_run = time.time() - t_run_start

print(f"\n{'='*80}")
print(f"RÉSULTATS - {bars_processed} BARS PROCESSED")
print(f"{'='*80}")
print(f"Run time: {t_run:.2f}s")
print(f"Avg per bar: {t_run/bars_processed*1000:.1f}ms")

# ANALYSE INSTRUMENTATION INTERNE
instrumentation = engine.market_state_engine._instrumentation_log

print(f"\n{'='*80}")
print(f"CREATE_MARKET_STATE CALLS")
print(f"{'='*80}")
print(f"Total calls: {len(instrumentation)}")
print(f"Cache misses logged: {len(cache_miss_log)}")

# ASSERT cohérence
if len(instrumentation) != len(cache_miss_log):
    print(f"⚠️  WARNING: instrumentation ({len(instrumentation)}) != cache_miss_log ({len(cache_miss_log)})")

if len(instrumentation) == 0:
    print("\n❌ NO create_market_state CALLS - Flow not working")
    sys.exit(1)

# BREAKDOWN (moyenne + P95)
import numpy as np

t_detect = [i['t_detect_structure_ms'] for i in instrumentation]
t_bias = [i['t_bias_calc_ms'] for i in instrumentation]
t_profile = [i['t_profile_confluence_ms'] for i in instrumentation]
t_finalize = [i['t_finalize_ms'] for i in instrumentation]
t_total = [i['t_total_ms'] for i in instrumentation]

print(f"\n{'='*80}")
print(f"BREAKDOWN (moyenne / P95)")
print(f"{'='*80}")
print(f"detect_structure:   {np.mean(t_detect):.2f}ms / {np.percentile(t_detect, 95):.2f}ms")
print(f"bias_calc:          {np.mean(t_bias):.2f}ms / {np.percentile(t_bias, 95):.2f}ms")
print(f"profile_confluence: {np.mean(t_profile):.2f}ms / {np.percentile(t_profile, 95):.2f}ms")
print(f"finalize:           {np.mean(t_finalize):.2f}ms / {np.percentile(t_finalize, 95):.2f}ms")
print(f"TOTAL:              {np.mean(t_total):.2f}ms / {np.percentile(t_total, 95):.2f}ms")

# Pourcentages
pct_detect = np.mean(t_detect) / np.mean(t_total) * 100
pct_bias = np.mean(t_bias) / np.mean(t_total) * 100
pct_profile = np.mean(t_profile) / np.mean(t_total) * 100

print(f"\nPourcentages:")
print(f"  detect_structure: {pct_detect:.1f}%")
print(f"  bias_calc: {pct_bias:.1f}%")
print(f"  profile_confluence: {pct_profile:.1f}%")

# TOP goulot
if pct_detect > max(pct_bias, pct_profile):
    print(f"\n🚨 GOULOT: detect_structure ({pct_detect:.0f}%)")
elif pct_bias > pct_profile:
    print(f"\n🚨 GOULOT: bias_calc ({pct_bias:.0f}%)")
else:
    print(f"\n🚨 GOULOT: profile_confluence ({pct_profile:.0f}%)")

# Candles analyzed
avg_daily = np.mean([i['daily_candles'] for i in instrumentation])
avg_h4 = np.mean([i['h4_candles'] for i in instrumentation])
avg_h1 = np.mean([i['h1_candles'] for i in instrumentation])

print(f"\nCandles analyzed (avg):")
print(f"  Daily: {avg_daily:.1f}")
print(f"  4H: {avg_h4:.1f}")
print(f"  1H: {avg_h1:.1f}")

# Cache miss reasons
miss_reasons = {
    '1h_close': sum(1 for m in cache_miss_log if m['is_close_1h']),
    '4h_close': sum(1 for m in cache_miss_log if m['is_close_4h']),
    '1d_close': sum(1 for m in cache_miss_log if m['is_close_1d']),
}

print(f"\n{'='*80}")
print(f"CACHE MISS ANALYSIS")
print(f"{'='*80}")
print(f"Total misses: {len(cache_miss_log)}")
print(f"Miss rate: {len(cache_miss_log)/bars_processed*100:.1f}%")
print(f"Miss frequency: 1 every {bars_processed/len(cache_miss_log):.1f} bars")

print(f"\nMiss causes:")
for reason, count in miss_reasons.items():
    pct = count / len(cache_miss_log) * 100 if cache_miss_log else 0
    print(f"  {reason}: {count} ({pct:.1f}%)")

# EXTRAPOLATION 1 JOUR (390 bars)
print(f"\n{'='*80}")
print(f"EXTRAPOLATION 1 JOUR (390 bars)")
print(f"{'='*80}")

miss_rate = len(cache_miss_log) / bars_processed
est_misses_1day = int(390 * miss_rate)
cost_per_miss = np.mean(t_total)
total_cost_misses_sec = est_misses_1day * cost_per_miss / 1000

# Reste du code (patterns, playbooks, etc)
avg_ms_per_bar = t_run / bars_processed * 1000
non_market_state_cost = (avg_ms_per_bar * 390 - est_misses_1day * cost_per_miss) / 1000

total_1day_sec = total_cost_misses_sec + non_market_state_cost

print(f"Miss rate: {miss_rate*100:.1f}%")
print(f"Estimated misses on 1 day: {est_misses_1day}")
print(f"Cost per miss: {cost_per_miss:.1f}ms")
print(f"Time in create_market_state: {total_cost_misses_sec:.2f}s")
print(f"Time in other code: {non_market_state_cost:.2f}s")
print(f"TOTAL 1 day: {total_1day_sec:.2f}s = {total_1day_sec/60:.2f} minutes")

if total_1day_sec <= 900:
    print(f"\n✅ TARGET MET: <15 minutes")
else:
    print(f"\n⚠️  Need {total_1day_sec/900:.1f}x speedup")

# Save JSON summary
summary = {
    'processed_bars': bars_processed,
    'create_market_state_calls': len(instrumentation),
    'breakdown_avg': {
        'detect_structure_ms': np.mean(t_detect),
        'bias_calc_ms': np.mean(t_bias),
        'profile_confluence_ms': np.mean(t_profile),
        'finalize_ms': np.mean(t_finalize),
        'total_ms': np.mean(t_total)
    },
    'breakdown_p95': {
        'detect_structure_ms': np.percentile(t_detect, 95),
        'bias_calc_ms': np.percentile(t_bias, 95),
        'profile_confluence_ms': np.percentile(t_profile, 95),
        'finalize_ms': np.percentile(t_finalize, 95),
        'total_ms': np.percentile(t_total, 95)
    },
    'cache_miss_rate': miss_rate,
    'est_1day_sec': total_1day_sec
}

with open('/tmp/p05b_summary.json', 'w') as f:
    json.dump(summary, f, indent=2)

print(f"\n✅ Summary saved to /tmp/p05b_summary.json")

# Top 20 lignes les plus coûteuses
print(f"\n{'='*80}")
print(f"TOP 20 MOST EXPENSIVE CALLS")
print(f"{'='*80}")

sorted_instr = sorted(instrumentation, key=lambda x: x['t_total_ms'], reverse=True)[:20]
for i, entry in enumerate(sorted_instr, 1):
    print(f"{i:2d}. {entry['t_total_ms']:.1f}ms (detect={entry['t_detect_structure_ms']:.1f}ms, bias={entry['t_bias_calc_ms']:.1f}ms)")

print(f"\n{'='*80}")
