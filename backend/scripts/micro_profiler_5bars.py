#!/usr/bin/env python3
"""
Micro-profiler bar-level - 5 bars max
Mesure temps par étape + call counts + cache behavior
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

# Monkey patch pour instrumenter _process_bar_optimized
original_process_bar = BacktestEngine._process_bar_optimized

call_counts = {
    'create_market_state': 0,
    'detect_structure': 0,
    'detect_patterns_ict': 0,
    'evaluate_playbooks': 0
}

bar_timings = []

def instrumented_process_bar(self, symbol, current_time, htf_events):
    """Version instrumentée qui mesure chaque étape"""
    t_start = time.perf_counter()
    
    # 1. Agrégateur (déjà fait avant cet appel, mais on mesure l'accès)
    t0 = time.perf_counter()
    candles_1m = self.tf_aggregator.get_candles(symbol, "1m")
    candles_5m = self.tf_aggregator.get_candles(symbol, "5m")
    candles_15m = self.tf_aggregator.get_candles(symbol, "15m")
    candles_1h = self.tf_aggregator.get_candles(symbol, "1h")
    candles_4h = self.tf_aggregator.get_candles(symbol, "4h")
    candles_1d = self.tf_aggregator.get_candles(symbol, "1d")
    t_agg = (time.perf_counter() - t0) * 1000
    
    if len(candles_1m) < 50 or len(candles_5m) < 5 or len(candles_1h) < 2:
        return None
    
    # 2. Market State (avec cache)
    t0 = time.perf_counter()
    from utils.timeframes import get_session_info
    if current_time.tzinfo is None:
        from datetime import timezone
        current_time = current_time.replace(tzinfo=timezone.utc)
    session_info = get_session_info(current_time, debug_log=False)
    current_session = session_info.get('session', 'Unknown')
    
    last_1h_close = candles_1h[-1].timestamp if candles_1h else None
    last_4h_close = candles_4h[-1].timestamp if candles_4h else None
    last_1d_close = candles_1d[-1].timestamp if candles_1d else None
    
    cache_key = self.market_state_cache.get_cache_key(
        symbol, current_session, last_1h_close, last_4h_close, last_1d_close
    )
    
    should_recalc = self.market_state_cache.should_recalculate(symbol, cache_key)
    cache_miss = should_recalc or htf_events.get("is_close_1h") or htf_events.get("is_close_4h") or htf_events.get("is_close_1d")
    
    if cache_miss:
        call_counts['create_market_state'] += 1
        multi_tf_data = {
            "1m": candles_1m[-500:],
            "5m": candles_5m[-200:],
            "15m": candles_15m[-100:],
            "1h": candles_1h[-50:],
            "4h": candles_4h[-20:],
            "1d": candles_1d[-10:]
        }
        
        market_state = self.market_state_engine.create_market_state(
            symbol,
            multi_tf_data,
            {
                "session": current_session,
                "current_time": current_time,
                "volatility": 0.0
            }
        )
        
        self.market_state_cache.put(cache_key, market_state)
    else:
        market_state = self.market_state_cache.get(cache_key)
        if market_state is None:
            # Fallback
            call_counts['create_market_state'] += 1
            multi_tf_data = {
                "1m": candles_1m[-500:],
                "5m": candles_5m[-200:],
                "15m": candles_15m[-100:],
                "1h": candles_1h[-50:],
                "4h": candles_4h[-20:],
                "1d": candles_1d[-10:]
            }
            market_state = self.market_state_engine.create_market_state(
                symbol, multi_tf_data,
                {"session": current_session, "current_time": current_time, "volatility": 0.0}
            )
            self.market_state_cache.put(cache_key, market_state)
    
    t_market_state = (time.perf_counter() - t0) * 1000
    
    # 3. Patterns
    t0 = time.perf_counter()
    ict_patterns = []
    candle_patterns = []
    
    patterns_called = 0
    if htf_events.get("is_close_5m") or htf_events.get("is_close_15m"):
        patterns_called = 1
        call_counts['detect_patterns_ict'] += 1
        
        if len(candles_5m) > 10:
            raw_candle_patterns = self.candlestick_engine.detect_patterns(candles_5m[-100:], timeframe="5m")
            candle_patterns = self._convert_candlestick_patterns(raw_candle_patterns)
        
        if len(candles_5m) > 10:
            ict_patterns.extend(self.ict_engine.detect_bos(candles_5m[-100:], timeframe="5m"))
            ict_patterns.extend(self.ict_engine.detect_fvg(candles_5m[-100:], timeframe="5m"))
        
        if len(candles_15m) > 10 and htf_events.get("is_close_15m"):
            ict_patterns.extend(self.ict_engine.detect_fvg(candles_15m[-100:], timeframe="15m"))
    
    t_patterns = (time.perf_counter() - t0) * 1000
    
    # 4. Generate setups
    t0 = time.perf_counter()
    call_counts['evaluate_playbooks'] += 1
    setups = self.setup_engine.generate_setups(
        symbol=symbol,
        current_time=current_time,
        market_state=market_state,
        ict_patterns=ict_patterns,
        candle_patterns=candle_patterns,
        liquidity_levels=[],
        trading_mode=self.config.trading_mode
    )
    t_playbooks = (time.perf_counter() - t0) * 1000
    
    if not setups:
        t_total = (time.perf_counter() - t_start) * 1000
        bar_timings.append({
            'ts': current_time.isoformat(),
            't_agg_ms': t_agg,
            't_market_state_ms': t_market_state,
            't_patterns_ms': t_patterns,
            't_playbooks_ms': t_playbooks,
            't_exec_ms': 0,
            't_total_ms': t_total,
            'cache_hit': 0 if cache_miss else 1,
            'cache_miss': 1 if cache_miss else 0,
            'patterns_called': patterns_called,
            'setups_generated': 0
        })
        return None
    
    # 5. Filter setups
    from engines.setup_engine_v2 import filter_setups_by_mode
    filtered_setups = filter_setups_by_mode(setups, self.risk_engine)
    
    if not filtered_setups:
        t_total = (time.perf_counter() - t_start) * 1000
        bar_timings.append({
            'ts': current_time.isoformat(),
            't_agg_ms': t_agg,
            't_market_state_ms': t_market_state,
            't_patterns_ms': t_patterns,
            't_playbooks_ms': t_playbooks,
            't_exec_ms': 0,
            't_total_ms': t_total,
            'cache_hit': 0 if cache_miss else 1,
            'cache_miss': 1 if cache_miss else 0,
            'patterns_called': patterns_called,
            'setups_generated': len(setups)
        })
        return None
    
    t_total = (time.perf_counter() - t_start) * 1000
    bar_timings.append({
        'ts': current_time.isoformat(),
        't_agg_ms': t_agg,
        't_market_state_ms': t_market_state,
        't_patterns_ms': t_patterns,
        't_playbooks_ms': t_playbooks,
        't_exec_ms': 0,
        't_total_ms': t_total,
        'cache_hit': 0 if cache_miss else 1,
        'cache_miss': 1 if cache_miss else 0,
        'patterns_called': patterns_called,
        'setups_generated': len(filtered_setups)
    })
    
    return max(filtered_setups, key=lambda s: s.final_score)

# Monkey patch
BacktestEngine._process_bar_optimized = instrumented_process_bar

# Config
config = BacktestConfig(
    run_name='micro_profile_5bars',
    start_date=datetime(2024, 6, 12, 9, 30, 0),
    end_date=datetime(2024, 6, 12, 10, 0, 0),  # Large window, mais on arrête après 5
    symbols=['SPY'],
    data_paths=['/app/data/historical/1m/SPY.parquet'],
    initial_capital=10000.0,
    trading_mode='AGGRESSIVE',
    trade_types=['DAILY', 'SCALP']
)

print("="*80)
print("MICRO-PROFILER - 5 BARS MAX")
print("="*80)

print("\nLoading data...")
t_load_start = time.time()
engine = BacktestEngine(config)
engine.load_data()
t_load = time.time() - t_load_start

# Vérifier les données chargées
spy_candles = engine.candles_1m_by_timestamp.get('SPY', {})
first_ts = min(spy_candles.keys()) if spy_candles else None
last_ts = max(spy_candles.keys()) if spy_candles else None

print(f"Load time: {t_load:.2f}s")
print(f"Total 1m candles: {len(spy_candles)}")
print(f"Period: {first_ts} to {last_ts}")

# Run avec arrêt après 5 bars
print("\nRunning 5 bars...")

# Modifier run() pour s'arrêter après 5
original_run = engine.run

def run_5_bars():
    engine.equity_curve_r = [0.0]
    engine.equity_curve_dollars = [config.initial_capital]
    
    minutes = sorted(engine.combined_data["datetime"].unique())
    print(f"Total bars available: {len(minutes)}")
    print(f"Processing first 5 bars...\n")
    
    for idx, current_time in enumerate(minutes[:100]):  # 100 bars pour avoir assez d'historique
        if idx % 10 == 0:  # Log tous les 10 bars
            print(f"Bar {idx+1}/100: {current_time.isoformat()}")
        
        # Ajouter bougies à l'agrégateur
        htf_events = {}
        for symbol in engine.config.symbols:
            candle_1m = engine.candles_1m_by_timestamp.get(symbol, {}).get(current_time)
            if candle_1m is None:
                continue
            events = engine.tf_aggregator.add_1m_candle(candle_1m)
            htf_events[symbol] = events
        
        # Process bar (instrumenté)
        candidate_setups = []
        for symbol in engine.config.symbols:
            events = htf_events.get(symbol, {})
            setup = engine._process_bar_optimized(symbol, current_time, events)
            if setup is not None:
                candidate_setups.append(setup)
        
        # Log immédiat
        if bar_timings:
            timing = bar_timings[-1]
            print(f"  t_agg={timing['t_agg_ms']:.1f}ms, t_market_state={timing['t_market_state_ms']:.1f}ms, " +
                  f"t_patterns={timing['t_patterns_ms']:.1f}ms, t_playbooks={timing['t_playbooks_ms']:.1f}ms, " +
                  f"t_total={timing['t_total_ms']:.1f}ms")
            print(f"  cache_hit={timing['cache_hit']}, patterns_called={timing['patterns_called']}, setups={timing['setups_generated']}")
    
    return None

engine.run = run_5_bars

t_run_start = time.time()
engine.run()
t_run = time.time() - t_run_start

print(f"\n{'='*80}")
print("RESULTS - 100 BARS")
print(f"{'='*80}")
print(f"Total run time: {t_run:.2f}s")
print(f"Bars processed: {len(bar_timings)}")
if len(bar_timings) > 0:
    print(f"Avg per bar: {t_run/len(bar_timings):.2f}s = {t_run/len(bar_timings)*1000:.0f}ms")

# Agrégats
if len(bar_timings) == 0:
    print("\n⚠️  No bars were processed (all skipped due to insufficient history)")
    sys.exit(0)

avg_agg = sum(t['t_agg_ms'] for t in bar_timings) / len(bar_timings)
avg_market_state = sum(t['t_market_state_ms'] for t in bar_timings) / len(bar_timings)
avg_patterns = sum(t['t_patterns_ms'] for t in bar_timings) / len(bar_timings)
avg_playbooks = sum(t['t_playbooks_ms'] for t in bar_timings) / len(bar_timings)
avg_total = sum(t['t_total_ms'] for t in bar_timings) / len(bar_timings)

print(f"\nAVERAGES:")
print(f"  Aggregator: {avg_agg:.1f}ms")
print(f"  Market State: {avg_market_state:.1f}ms")
print(f"  Patterns: {avg_patterns:.1f}ms")
print(f"  Playbooks: {avg_playbooks:.1f}ms")
print(f"  Total: {avg_total:.1f}ms")

print(f"\nCALL COUNTS:")
print(f"  create_market_state: {call_counts['create_market_state']}")
print(f"  detect_patterns_ict: {call_counts['detect_patterns_ict']}")
print(f"  evaluate_playbooks: {call_counts['evaluate_playbooks']}")

cache_hits = sum(t['cache_hit'] for t in bar_timings)
cache_misses = sum(t['cache_miss'] for t in bar_timings)
cache_total = cache_hits + cache_misses
hit_rate = (cache_hits / cache_total * 100) if cache_total > 0 else 0

print(f"\nCACHE BEHAVIOR:")
print(f"  Hits: {cache_hits}")
print(f"  Misses: {cache_misses}")
print(f"  Hit rate: {hit_rate:.1f}%")

print(f"\n{'='*80}")
print("BOTTLENECK ANALYSIS:")
pct_market_state = (avg_market_state / avg_total * 100) if avg_total > 0 else 0
pct_patterns = (avg_patterns / avg_total * 100) if avg_total > 0 else 0
pct_playbooks = (avg_playbooks / avg_total * 100) if avg_total > 0 else 0

print(f"  Market State: {pct_market_state:.1f}% of total time")
print(f"  Patterns: {pct_patterns:.1f}% of total time")
print(f"  Playbooks: {pct_playbooks:.1f}% of total time")

if pct_market_state > 50:
    print(f"\n🚨 GOULOT: Market State ({pct_market_state:.0f}%)")
elif pct_patterns > 50:
    print(f"\n🚨 GOULOT: Patterns ({pct_patterns:.0f}%)")
elif pct_playbooks > 50:
    print(f"\n🚨 GOULOT: Playbooks ({pct_playbooks:.0f}%)")
else:
    print(f"\n⚠️  Coût réparti, pas de goulot unique >50%")
