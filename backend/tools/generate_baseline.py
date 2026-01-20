#!/usr/bin/env python3
"""
Génération BASELINE (BEFORE patch) pour comparaison objective
Execute une évaluation SANS les bypasses AGGRESSIVE pour obtenir le state BEFORE
"""
import sys
import json
import os
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent))

# FORCER SAFE pour simuler BEFORE
os.environ['TRADING_MODE'] = 'SAFE'

from engines.playbook_loader import get_playbook_loader, PlaybookEvaluator
from engines.patterns.custom_detectors import detect_custom_patterns
from models.market_data import Candle
import pandas as pd

def generate_baseline():
    """Génère les stats BEFORE patch (mode SAFE, pas de bypass)"""
    
    print("\n" + "="*70)
    print("BASELINE GENERATION (BEFORE PATCH)")
    print("="*70)
    
    loader = get_playbook_loader()
    evaluator = PlaybookEvaluator(loader)
    
    from config.settings import settings
    print(f"\n✅ MODE: {settings.TRADING_MODE} (simulating BEFORE state)")
    
    # Load playbooks for both modes
    playbooks_all = loader.playbooks
    print(f"✅ Total playbooks: {len(playbooks_all)}")
    
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
    
    # Market state
    market_state = {
        'bias': 'bullish',
        'current_session': 'NY',
        'daily_structure': 'bullish',
        'h4_structure': 'bullish',
        'h1_structure': 'bullish',
        'session_profile': {}
    }
    
    current_time = candles_1m[50].timestamp
    
    # STATS
    stats = {
        'mode': 'SAFE',
        'description': 'BASELINE (BEFORE patch)',
        'setups_total': 100,  # Sample size
        'symbols': ['SPY'],
        'total_playbooks': len(playbooks_all),
        'playbook_matches_total': 0,
        'matched_count': 0,
        'reject_count': 0,
        'matches_by_playbook': {},
        'rejections_by_reason': {},
        'relaxed_bypasses': {
            'relaxed_structure_htf': 0,
            'relaxed_candlestick_patterns': 0,
            'relaxed_ict_patterns_empty': 0,
            'total': 0
        }
    }
    
    print(f"\n🔍 Evaluating {len(playbooks_all)} playbooks (SAFE mode):")
    print("-" * 70)
    
    # Evaluate all playbooks
    for playbook in playbooks_all:
        basic_pass, basic_reason = evaluator._check_basic_filters(
            playbook, 'SPY', current_time, market_state
        )
        
        if not basic_pass:
            stats['reject_count'] += 1
            stats['rejections_by_reason'][basic_reason] = stats['rejections_by_reason'].get(basic_reason, 0) + 1
            continue
        
        score, details = evaluator._evaluate_playbook_conditions(
            playbook,
            market_state,
            ict_patterns,
            []  # No candlestick patterns
        )
        
        if score is None:
            stats['reject_count'] += 1
            # Identify specific reason
            reason = 'score_none_structure_htf_or_patterns'
            stats['rejections_by_reason'][reason] = stats['rejections_by_reason'].get(reason, 0) + 1
            continue
        
        # Match
        grade = evaluator._calculate_grade(score, playbook.grade_thresholds)
        stats['matched_count'] += 1
        stats['playbook_matches_total'] += 1
        stats['matches_by_playbook'][playbook.name] = {
            'count': 1,
            'score': score,
            'grade': grade
        }
    
    print(f"\n✅ Matched: {stats['matched_count']}")
    print(f"❌ Rejected: {stats['reject_count']}")
    
    # Save baseline
    output_path = Path(str(results_path('playbook_match_stats_2025-06_before.json')))
    with open(output_path, 'w') as f:
        json.dump(stats, f, indent=2)
    
    print(f"\n✅ BASELINE saved: {output_path}")
    return stats

if __name__ == '__main__':
    generate_baseline()
