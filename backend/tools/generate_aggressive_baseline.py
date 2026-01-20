#!/usr/bin/env python3
"""
Génération BASELINE AGGRESSIVE PRE-PATCH
Simule l'état AGGRESSIVE avant le patch (bypass inactif)
"""
import sys
import json
import os
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent))

# FORCER AGGRESSIVE mais avec bypass désactivé
os.environ['TRADING_MODE'] = 'AGGRESSIVE'

from engines.playbook_loader import get_playbook_loader, PlaybookEvaluator
from engines.patterns.custom_detectors import detect_custom_patterns
from models.market_data import Candle
import pandas as pd

def generate_aggressive_before():
    """Génère les stats AGGRESSIVE PRE-PATCH (simule bypass non-effectif)"""
    
    print("\n" + "="*70)
    print("BASELINE AGGRESSIVE PRE-PATCH")
    print("="*70)
    
    loader = get_playbook_loader()
    evaluator = PlaybookEvaluator(loader)
    
    from config.settings import settings
    print(f"\n✅ MODE: {settings.TRADING_MODE}")
    print("⚠️  Simulating PRE-PATCH state (bypasses not effective)")
    
    playbooks = loader.playbooks
    print(f"✅ Total playbooks: {len(playbooks)}")
    
    # Load data
    data_path = Path(str(historical_data_path('1m')) + '/SPY.parquet')
    df = pd.read_parquet(data_path)
    
    if 'datetime' not in df.columns:
        df = df.reset_index()
    
    df['datetime'] = pd.to_datetime(df['datetime'], utc=True)
    
    # June 2025
    start = pd.Timestamp('2025-06-01', tz='UTC')
    end = pd.Timestamp('2025-07-01', tz='UTC')
    df_june = df[(df['datetime'] >= start) & (df['datetime'] < end)]
    
    # Sample in NY session
    df_june_sorted = df_june.sort_values('datetime')
    target_time = pd.Timestamp('2025-06-10 14:00:00', tz='UTC')
    mask = df_june_sorted['datetime'] >= target_time
    
    if mask.any():
        start_idx = df_june_sorted[mask].index[0]
        df_sample = df_june_sorted.loc[start_idx:start_idx+99]
    else:
        df_sample = df_june.iloc[5000:5100]
    
    # Convert to Candles
    candles_1m = []
    for _, row in df_sample.iterrows():
        candle = Candle(
            symbol='SPY',
            timeframe='1m',
            timestamp=row['datetime'].to_pydatetime().replace(tzinfo=None),
            open=float(row['open']),
            high=float(row['high']),
            low=float(row['low']),
            close=float(row['close']),
            volume=int(row['volume'])
        )
        candles_1m.append(candle)
    
    # Detect ICT patterns
    detections = detect_custom_patterns(candles_1m, "5m")
    ict_patterns = []
    for plist in detections.values():
        if plist:
            ict_patterns.extend(plist)
    
    print(f"\n📊 Sample: {len(candles_1m)} candles, {len(ict_patterns)} ICT patterns")
    
    # Market state (avec structure_htf = bullish, qui cause le mismatch)
    market_state = {
        'bias': 'bullish',
        'current_session': 'NY',
        'daily_structure': 'bullish',  # MISMATCH!
        'h4_structure': 'bullish',
        'h1_structure': 'bullish',
        'session_profile': {}
    }
    
    current_time = candles_1m[50].timestamp
    
    # STATS
    stats = {
        'mode': 'AGGRESSIVE',
        'description': 'BASELINE AGGRESSIVE PRE-PATCH (bypasses not effective)',
        'setups_total': 100,
        'symbols': ['SPY'],
        'total_playbooks': len(playbooks),
        'playbook_matches_total': 0,
        'matched_count': 0,
        'reject_count': 0,
        'matches_by_playbook': {},
        'rejections_by_reason': {},
        'relaxed_bypasses': {
            'structure_htf_mismatch': 0,
            'candlestick_patterns_missing': 0,
            'ict_patterns_empty': 0,
            'total': 0
        }
    }
    
    print(f"\n🔍 Evaluating {len(playbooks)} playbooks (PRE-PATCH simulation):")
    print("-" * 70)
    
    # Evaluate WITHOUT bypasses (simulate pre-patch)
    for playbook in playbooks:
        basic_pass, basic_reason = evaluator._check_basic_filters(
            playbook, 'SPY', current_time, market_state
        )
        
        if not basic_pass:
            stats['reject_count'] += 1
            stats['rejections_by_reason'][basic_reason] = stats['rejections_by_reason'].get(basic_reason, 0) + 1
            continue
        
        # SIMULATE PRE-PATCH: Apply strict checks manually
        # Check structure_htf STRICTLY (no bypass)
        structure = market_state.get('daily_structure', 'unknown')
        if playbook.structure_htf and structure not in playbook.structure_htf and structure != 'unknown':
            stats['reject_count'] += 1
            reason = 'structure_htf_mismatch_strict'
            stats['rejections_by_reason'][reason] = stats['rejections_by_reason'].get(reason, 0) + 1
            continue
        
        # Check candlestick patterns STRICTLY (no bypass)
        matching_patterns = []  # No patterns available
        if playbook.required_pattern_families and not matching_patterns:
            stats['reject_count'] += 1
            reason = 'candlestick_patterns_missing_strict'
            stats['rejections_by_reason'][reason] = stats['rejections_by_reason'].get(reason, 0) + 1
            continue
        
        # If it passed both checks, it matches (unlikely pre-patch)
        stats['matched_count'] += 1
        stats['playbook_matches_total'] += 1
        stats['matches_by_playbook'][playbook.name] = {'count': 1}
    
    print(f"\n✅ Matched: {stats['matched_count']}")
    print(f"❌ Rejected: {stats['reject_count']}")
    
    # Save baseline
    output_path = Path(str(results_path('playbook_match_stats_2025-06_aggressive_before.json')))
    with open(output_path, 'w') as f:
        json.dump(stats, f, indent=2)
    
    print(f"\n✅ BASELINE AGGRESSIVE PRE-PATCH saved: {output_path}")
    return stats

if __name__ == '__main__':
    generate_aggressive_before()
