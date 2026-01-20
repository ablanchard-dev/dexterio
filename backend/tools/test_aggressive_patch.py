#!/usr/bin/env python3
"""
Test COMPLET du patch AGGRESSIVE avec stats repo-level
Usage: python -m tools.test_aggressive_patch --month 2025-06
"""
import sys
import json
import os
import argparse
from pathlib import Path
from collections import Counter
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

# FORCER LE MODE AGGRESSIVE
os.environ['TRADING_MODE'] = 'AGGRESSIVE'

from engines.playbook_loader import get_playbook_loader, PlaybookEvaluator
from engines.patterns.custom_detectors import detect_custom_patterns
from models.market_data import Candle
import pandas as pd

def test_aggressive_patch(month: str):
    """Test le patch AGGRESSIVE avec preuves stats complètes"""
    
    print("\n" + "="*70)
    print(f"TEST PATCH AGGRESSIVE - {month}")
    print("="*70)
    
    # Load playbooks
    loader = get_playbook_loader()
    evaluator = PlaybookEvaluator(loader)
    
    from config.settings import settings
    print(f"\n✅ TRADING_MODE: {settings.TRADING_MODE}")
    
    playbooks = loader.playbooks
    print(f"✅ Total playbooks: {len(playbooks)}")
    
    # Load data for both symbols
    symbols_data = {}
    for symbol in ['SPY', 'QQQ']:
        data_path = Path(fstr(historical_data_path('1m')) + '/{symbol}.parquet')
        if not data_path.exists():
            print(f"⚠️  {symbol}: data not found, skipping")
            continue
        
        df = pd.read_parquet(data_path)
        
        if 'datetime' not in df.columns:
            df = df.reset_index()
        
        df['datetime'] = pd.to_datetime(df['datetime'], utc=True)
        
        # Filter month
        year, mon = month.split('-')
        start = pd.Timestamp(f'{year}-{mon}-01', tz='UTC')
        if int(mon) == 12:
            end = pd.Timestamp(f'{int(year)+1}-01-01', tz='UTC')
        else:
            end = pd.Timestamp(f'{year}-{int(mon)+1:02d}-01', tz='UTC')
        
        df_month = df[(df['datetime'] >= start) & (df['datetime'] < end)]
        symbols_data[symbol] = df_month
    
    print(f"\n📊 Data loaded:")
    for symbol, df in symbols_data.items():
        print(f"  {symbol}: {len(df)} bars")
    
    # STATS GLOBALES
    stats = {
        'month': month,
        'mode': settings.TRADING_MODE,
        'timestamp': datetime.utcnow().isoformat(),
        'symbols': list(symbols_data.keys()),
        'setups_total': sum(len(df) for df in symbols_data.values()),
        'total_playbooks': len(playbooks),
        'playbook_matches_total': 0,
        'matched_count': 0,
        'reject_count': 0,
        'matches_by_playbook': {},
        'matches_by_symbol': {},
        'rejections_by_reason': {},
        'relaxed_bypasses': {
            'structure_htf_mismatch': 0,
            'candlestick_patterns_missing': 0,
            'ict_patterns_empty': 0,
            'total': 0
        }
    }
    
    # Test sur échantillon pour chaque symbole
    for symbol, df_month in symbols_data.items():
        print(f"\n🔍 Testing {symbol}:")
        print("-" * 70)
        
        stats['matches_by_symbol'][symbol] = {
            'matched': 0,
            'rejected': 0
        }
        
        # Sample in NY session (14:00 UTC = 10:00 ET)
        df_sorted = df_month.sort_values('datetime')
        target_time = pd.Timestamp(f'{year}-{mon}-10 14:00:00', tz='UTC')
        mask = df_sorted['datetime'] >= target_time
        
        if mask.any():
            start_idx = df_sorted[mask].index[0]
            df_sample = df_sorted.loc[start_idx:start_idx+99]
        else:
            df_sample = df_month.iloc[5000:5100]
        
        # Convert to Candles
        candles_1m = []
        for _, row in df_sample.iterrows():
            candle = Candle(
                symbol=symbol,
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
        
        print(f"  📊 Sample: {len(candles_1m)} candles, {len(ict_patterns)} ICT patterns")
        
        # Get current time first
        current_time = candles_1m[50].timestamp if len(candles_1m) > 50 else candles_1m[0].timestamp
        
        # Market state - UTILISER LE VRAI MARKET STATE ENGINE
        from engines.market_state import MarketStateEngine
        mse = MarketStateEngine()
        
        # Préparer les timeframes HTF (simulés depuis les 1m)
        # Pour un test rapide, on simule avec peu de données
        daily_candles = candles_1m[-10:] if len(candles_1m) >= 10 else candles_1m
        h4_candles = candles_1m[-20:] if len(candles_1m) >= 20 else candles_1m
        h1_candles = candles_1m[-50:] if len(candles_1m) >= 50 else candles_1m
        
        # Créer le market_state via le vrai engine
        market_state_obj = mse.create_market_state(
            symbol=symbol,
            multi_tf_data={
                '1m': candles_1m,
                '5m': candles_1m,  # Simplified
                '15m': candles_1m,
                '1h': h1_candles,
                '4h': h4_candles,
                '1d': daily_candles
            },
            session_info={
                'name': 'NY',
                'session_levels': {}
            }
        )
        
        # Convertir en dict pour compatibilité
        market_state = {
            'bias': market_state_obj.bias,
            'current_session': 'NY',
            'daily_structure': market_state_obj.daily_structure,
            'h4_structure': market_state_obj.h4_structure,
            'h1_structure': market_state_obj.h1_structure,
            'session_profile': market_state_obj.session_profile,
            'day_type': market_state_obj.day_type  # P1: Add day_type
        }
        
        print(f"  🔧 Market state: bias={market_state['bias']}, daily_structure={market_state['daily_structure']}, day_type={market_state['day_type']}")
        
        # Evaluate all playbooks
        for playbook in playbooks:
            basic_pass, basic_reason = evaluator._check_basic_filters(
                playbook, symbol, current_time, market_state
            )
            
            if not basic_pass:
                stats['reject_count'] += 1
                stats['matches_by_symbol'][symbol]['rejected'] += 1
                stats['rejections_by_reason'][basic_reason] = stats['rejections_by_reason'].get(basic_reason, 0) + 1
                continue
            
            # ÉVALUATION AVEC PATCH
            score, details = evaluator._evaluate_playbook_conditions(
                playbook,
                market_state,
                ict_patterns,
                []  # No candlestick patterns (test du bypass)
            )
            
            if score is None:
                stats['reject_count'] += 1
                stats['matches_by_symbol'][symbol]['rejected'] += 1
                stats['rejections_by_reason']['score_none'] = stats['rejections_by_reason'].get('score_none', 0) + 1
                continue
            
            # SUCCESS
            grade = evaluator._calculate_grade(score, playbook.grade_thresholds)
            stats['matched_count'] += 1
            stats['playbook_matches_total'] += 1
            stats['matches_by_symbol'][symbol]['matched'] += 1
            
            # Aggregate by playbook
            if playbook.name not in stats['matches_by_playbook']:
                stats['matches_by_playbook'][playbook.name] = {
                    'count': 0,
                    'scores': [],
                    'grade': grade
                }
            stats['matches_by_playbook'][playbook.name]['count'] += 1
            stats['matches_by_playbook'][playbook.name]['scores'].append(score)
            
            # Track bypasses
            if details.get('bypasses_applied'):
                for bypass in details['bypasses_applied']:
                    if 'structure_htf' in bypass:
                        stats['relaxed_bypasses']['structure_htf_mismatch'] += 1
                    elif 'candlestick' in bypass:
                        stats['relaxed_bypasses']['candlestick_patterns_missing'] += 1
                    elif 'ict_patterns' in bypass:
                        stats['relaxed_bypasses']['ict_patterns_empty'] += 1
                    stats['relaxed_bypasses']['total'] += 1
        
        print(f"  ✅ Matched: {stats['matches_by_symbol'][symbol]['matched']}")
        print(f"  ❌ Rejected: {stats['matches_by_symbol'][symbol]['rejected']}")
    
    # Calculate averages for matches
    for pb_name, data in stats['matches_by_playbook'].items():
        data['avg_score'] = sum(data['scores']) / len(data['scores']) if data['scores'] else 0
        del data['scores']  # Remove raw scores for clean JSON
    
    # Sort matches by count
    stats['matches_by_playbook'] = dict(sorted(
        stats['matches_by_playbook'].items(),
        key=lambda x: x[1]['count'],
        reverse=True
    ))
    
    print("\n" + "="*70)
    print("RÉSULTATS FINAUX")
    print("="*70)
    print(f"Setups total (bars): {stats['setups_total']}")
    print(f"Total playbooks: {stats['total_playbooks']}")
    print(f"✅ Playbooks matchés: {stats['matched_count']}")
    print(f"❌ Playbooks rejetés: {stats['reject_count']}")
    print(f"🔓 Bypasses AGGRESSIVE: {stats['relaxed_bypasses']['total']}")
    print(f"   - structure_htf: {stats['relaxed_bypasses']['structure_htf_mismatch']}")
    print(f"   - candlestick_patterns: {stats['relaxed_bypasses']['candlestick_patterns_missing']}")
    print(f"   - ict_patterns_empty: {stats['relaxed_bypasses']['ict_patterns_empty']}")
    
    if stats['matches_by_playbook']:
        print(f"\n🎯 Top 5 playbooks matchés:")
        for i, (name, data) in enumerate(list(stats['matches_by_playbook'].items())[:5], 1):
            print(f"  {i}. {name}: {data['count']} matches, avg_score={data['avg_score']:.3f}, grade={data['grade']}")
    
    print(f"\n⚠️  Top 5 rejets:")
    for i, (reason, count) in enumerate(sorted(stats['rejections_by_reason'].items(), key=lambda x: -x[1])[:5], 1):
        print(f"  {i}. {reason}: {count}")
    
    # Save stats
    output_path = Path(fstr(results_path('playbook_match_stats_{month}.json')))
    with open(output_path, 'w') as f:
        json.dump(stats, f, indent=2)
    
    print(f"\n✅ Stats sauvegardées: {output_path}")
    
    # Load BEFORE for comparison
    before_path = Path(fstr(results_path('playbook_match_stats_{month}_before.json')))
    if before_path.exists():
        with open(before_path) as f:
            before_stats = json.load(f)
        
        print(f"\n📊 COMPARAISON AVANT/APRÈS:")
        print(f"  Playbooks matchés: {before_stats.get('matched_count', 0)} → {stats['matched_count']}")
        delta = stats['matched_count'] - before_stats.get('matched_count', 0)
        print(f"  Delta: +{delta} ({delta / stats['total_playbooks'] * 100:.1f}% improvement)")
    
    # SUCCESS CRITERIA
    if stats['matched_count'] > 0:
        print(f"\n✅ P0 LOCKED: {stats['matched_count']} playbooks matchés en mode AGGRESSIVE")
        print("✅ Le funnel peut maintenant générer des setups")
        return 0
    else:
        print(f"\n❌ P0 BLOCKED: Aucun playbook matché malgré le patch")
        return 1

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--month', default='2025-06', help='Format YYYY-MM')
    args = parser.parse_args()
    
    exit_code = test_aggressive_patch(args.month)
    sys.exit(exit_code)
