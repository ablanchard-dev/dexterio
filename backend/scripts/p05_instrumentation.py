#!/usr/bin/env python3
"""
P0.5 - Instrumentation complète create_market_state() + run 500-1000 bars traitées
"""
import sys
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
logging.basicConfig(level=logging.ERROR)

from backtest.engine import BacktestEngine
from models.backtest import BacktestConfig

print("="*80)
print("P0.5 - INSTRUMENTATION create_market_state() + 500 BARS TRAITÉES")
print("="*80)

# Config : large window pour avoir warmup + run réel
config = BacktestConfig(
    run_name='p05_instrumentation',
    start_date=datetime(2024, 6, 2, 8, 0, 0),  # Début de journée
    end_date=datetime(2024, 6, 12, 16, 0, 0),  # ~10 jours pour avoir 500+ bars after warmup
    symbols=['SPY'],
    data_paths=['/app/data/historical/1m/SPY.parquet'],
    initial_capital=10000.0,
    trading_mode='AGGRESSIVE',
    trade_types=['DAILY', 'SCALP']
)

print("\nLoading data...")
t_load_start = time.time()
engine = BacktestEngine(config)
engine.load_data()
t_load = time.time() - t_load_start

spy_candles = engine.candles_1m_by_timestamp.get('SPY', {})
print(f"Load time: {t_load:.2f}s")
print(f"Total 1m candles: {len(spy_candles)}")

# Activer instrumentation dans MarketStateEngine
engine.market_state_engine._instrumentation_log = []

# Tracking global
bar_timings = []
call_counts = {
    'create_market_state': 0,
    'detect_structure': 0,  # Sera = create_market_state * 3 (daily/h4/h1)
    'evaluate_playbooks': 0
}

cache_misses_log = []

# Run avec arrêt après 500 bars traitées
print("\nRunning until 500 bars processed...")

minutes = sorted(engine.combined_data["datetime"].unique())
print(f"Total bars available: {len(minutes)}")

bars_processed = 0
TARGET_BARS = 500

t_run_start = time.time()

for idx, current_time in enumerate(minutes):
    if bars_processed >= TARGET_BARS:
        break
    
    # Ajouter bougies à l'agrégateur
    htf_events = {}
    for symbol in engine.config.symbols:
        candle_1m = engine.candles_1m_by_timestamp.get(symbol, {}).get(current_time)
        if candle_1m is None:
            continue
        events = engine.tf_aggregator.add_1m_candle(candle_1m)
        htf_events[symbol] = events
    
    # Check si on peut traiter (besoin historique minimum)
    candles_1m = engine.tf_aggregator.get_candles('SPY', '1m')
    candles_5m = engine.tf_aggregator.get_candles('SPY', '5m')
    candles_1h = engine.tf_aggregator.get_candles('SPY', '1h')
    
    if len(candles_1m) < 50 or len(candles_5m) < 5 or len(candles_1h) < 2:
        continue  # Skip warmup
    
    # Process bar
    t_bar_start = time.perf_counter()
    
    for symbol in engine.config.symbols:
        # Check cache
        from utils.timeframes import get_session_info
        from datetime import timezone
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)
        session_info = get_session_info(current_time, debug_log=False)
        current_session = session_info.get('session', 'Unknown')
        
        candles_1h_sym = engine.tf_aggregator.get_candles(symbol, '1h')
        candles_4h = engine.tf_aggregator.get_candles(symbol, '4h')
        candles_1d = engine.tf_aggregator.get_candles(symbol, '1d')
        
        last_1h = candles_1h_sym[-1].timestamp if candles_1h_sym else None
        last_4h = candles_4h[-1].timestamp if candles_4h else None
        last_1d = candles_1d[-1].timestamp if candles_1d else None
        
        cache_key = engine.market_state_cache.get_cache_key(
            symbol, current_session, last_1h, last_4h, last_1d
        )
        
        should_recalc = engine.market_state_cache.should_recalculate(symbol, cache_key)
        events = htf_events.get(symbol, {})
        cache_miss = should_recalc or events.get("is_close_1h") or events.get("is_close_4h") or events.get("is_close_1d")
        
        if cache_miss:
            call_counts['create_market_state'] += 1
            cache_misses_log.append({
                'bar_idx': bars_processed,
                'ts': current_time.isoformat(),
                'session': current_session,
                'is_close_1h': events.get('is_close_1h', False),
                'is_close_4h': events.get('is_close_4h', False),
                'is_close_1d': events.get('is_close_1d', False)
            })
    
    t_bar = (time.perf_counter() - t_bar_start) * 1000
    bar_timings.append(t_bar)
    
    bars_processed += 1
    
    if bars_processed % 100 == 0:
        print(f"  Processed {bars_processed}/{TARGET_BARS} bars...")

t_run = time.time() - t_run_start

print(f"\n{'='*80}")
print(f"RESULTS - {bars_processed} BARS PROCESSED")
print(f"{'='*80}")
print(f"Total run time: {t_run:.2f}s")
print(f"Avg per bar: {t_run/bars_processed*1000:.1f}ms")

# Analyse cache miss frequency
total_misses = call_counts['create_market_state']
hit_rate = (1 - total_misses / bars_processed) * 100 if bars_processed > 0 else 0

print(f"\n📊 CACHE BEHAVIOR (sur {bars_processed} bars traitées)")
print(f"  Cache misses: {total_misses}")
print(f"  Hit rate: {hit_rate:.1f}%")
print(f"  Miss frequency: 1 miss every {bars_processed/total_misses:.1f} bars" if total_misses > 0 else "  No misses")

# Reasons for misses
misses_by_reason = {
    '1h_close': sum(1 for m in cache_misses_log if m['is_close_1h']),
    '4h_close': sum(1 for m in cache_misses_log if m['is_close_4h']),
    '1d_close': sum(1 for m in cache_misses_log if m['is_close_1d']),
    'other': sum(1 for m in cache_misses_log if not any([m['is_close_1h'], m['is_close_4h'], m['is_close_1d']]))
}

print(f"\n  Miss reasons:")
for reason, count in misses_by_reason.items():
    pct = count / total_misses * 100 if total_misses > 0 else 0
    print(f"    {reason}: {count} ({pct:.1f}%)")

# Analyse create_market_state() breakdown
instrumentation = engine.market_state_engine._instrumentation_log

if instrumentation:
    print(f"\n{'='*80}")
    print(f"create_market_state() BREAKDOWN ({len(instrumentation)} appels)")
    print(f"{'='*80}")
    
    avg_prepare = sum(i['t_prepare_ms'] for i in instrumentation) / len(instrumentation)
    avg_detect_structure = sum(i['t_detect_structure_ms'] for i in instrumentation) / len(instrumentation)
    avg_bias = sum(i['t_bias_calc_ms'] for i in instrumentation) / len(instrumentation)
    avg_profile = sum(i['t_profile_confluence_ms'] for i in instrumentation) / len(instrumentation)
    avg_finalize = sum(i['t_finalize_ms'] for i in instrumentation) / len(instrumentation)
    avg_total = sum(i['t_total_ms'] for i in instrumentation) / len(instrumentation)
    
    print(f"  Prepare inputs: {avg_prepare:.2f}ms")
    print(f"  Detect structure: {avg_detect_structure:.2f}ms ({avg_detect_structure/avg_total*100:.1f}%)")
    print(f"  Bias calc: {avg_bias:.2f}ms ({avg_bias/avg_total*100:.1f}%)")
    print(f"  Profile/confluence: {avg_profile:.2f}ms ({avg_profile/avg_total*100:.1f}%)")
    print(f"  Finalize: {avg_finalize:.2f}ms")
    print(f"  TOTAL: {avg_total:.2f}ms")
    
    # Candles analyzed
    avg_daily = sum(i['daily_candles'] for i in instrumentation) / len(instrumentation)
    avg_h4 = sum(i['h4_candles'] for i in instrumentation) / len(instrumentation)
    avg_h1 = sum(i['h1_candles'] for i in instrumentation) / len(instrumentation)
    
    print(f"\n  Avg candles analyzed:")
    print(f"    Daily: {avg_daily:.1f}")
    print(f"    4H: {avg_h4:.1f}")
    print(f"    1H: {avg_h1:.1f}")
    
    # Top goulot
    if avg_detect_structure > max(avg_bias, avg_profile):
        print(f"\n  🚨 GOULOT: detect_structure ({avg_detect_structure/avg_total*100:.0f}% du temps)")
    elif avg_bias > avg_profile:
        print(f"\n  🚨 GOULOT: bias_calc ({avg_bias/avg_total*100:.0f}% du temps)")
    else:
        print(f"\n  🚨 GOULOT: profile/confluence ({avg_profile/avg_total*100:.0f}% du temps)")

# Extrapolation 1 jour
print(f"\n{'='*80}")
print(f"EXTRAPOLATION 1 JOUR (390 bars)")
print(f"{'='*80}")

avg_ms_per_bar = t_run / bars_processed * 1000
est_1day_ms = avg_ms_per_bar * 390
est_1day_sec = est_1day_ms / 1000

print(f"  Avg per bar: {avg_ms_per_bar:.1f}ms")
print(f"  Est 1 day: {est_1day_sec:.1f}s = {est_1day_sec/60:.1f} minutes")

if est_1day_sec <= 900:
    print(f"  ✅ TARGET MET: <15 minutes")
else:
    print(f"  ⚠️  Need optimization: {est_1day_sec/900:.1f}x too slow")

# Impact cache miss sur 1 jour
if total_misses > 0 and instrumentation:
    miss_rate = total_misses / bars_processed
    est_misses_1day = int(390 * miss_rate)
    cost_per_miss = avg_total
    total_cost_misses = est_misses_1day * cost_per_miss / 1000
    
    print(f"\n  Cache miss impact on 1 day:")
    print(f"    Estimated misses: {est_misses_1day}")
    print(f"    Cost per miss: {cost_per_miss:.1f}ms")
    print(f"    Total time in create_market_state: {total_cost_misses:.1f}s")
    print(f"    % of total 1 day time: {total_cost_misses/est_1day_sec*100:.1f}%")

print(f"\n{'='*80}")
