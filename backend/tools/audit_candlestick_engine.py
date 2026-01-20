#!/usr/bin/env python3
"""
Audit Candlestick Patterns - P1-B
Vérifie si le moteur existe, est câblé, et détecte des patterns
"""
import sys
import json
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from engines.patterns.candlesticks import CandlestickPatternEngine
from models.market_data import Candle

def audit_candlestick_engine(month: str):
    """Audit complet du moteur candlestick"""
    
    print("\n" + "="*70)
    print(f"AUDIT CANDLESTICK ENGINE - {month}")
    print("="*70)
    
    # 1. Check engine exists
    print("\n1️⃣ ENGINE PRESENCE")
    try:
        engine = CandlestickPatternEngine()
        print("  ✅ CandlestickPatternEngine exists")
        print(f"  ✅ Class: {engine.__class__.__name__}")
        print(f"  ✅ Methods: {[m for m in dir(engine) if not m.startswith('_')]}")
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        return
    
    # 2. Load data and test detection
    print("\n2️⃣ PATTERN DETECTION TEST")
    
    data_path = Path(str(historical_data_path('1m')) + '/SPY.parquet')
    df = pd.read_parquet(data_path)
    
    if 'datetime' not in df.columns:
        df = df.reset_index()
    
    df['datetime'] = pd.to_datetime(df['datetime'], utc=True)
    
    # June 2025
    year, mon = month.split('-')
    start = pd.Timestamp(f'{year}-{mon}-01', tz='UTC')
    if int(mon) == 12:
        end = pd.Timestamp(f'{int(year)+1}-01-01', tz='UTC')
    else:
        end = pd.Timestamp(f'{year}-{int(mon)+1:02d}-01', tz='UTC')
    
    df_month = df[(df['datetime'] >= start) & (df['datetime'] < end)]
    
    # Sample in NY session
    df_sorted = df_month.sort_values('datetime')
    target_time = pd.Timestamp(f'{year}-{mon}-10 14:00:00', tz='UTC')
    mask = df_sorted['datetime'] >= target_time
    
    if mask.any():
        start_idx = df_sorted[mask].index[0]
        df_sample = df_sorted.loc[start_idx:start_idx+99]
    else:
        df_sample = df_month.iloc[5000:5100]
    
    # Convert to Candles
    candles = []
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
        candles.append(candle)
    
    print(f"  📊 Sample: {len(candles)} candles")
    
    # Detect on different timeframes
    results = {}
    for tf in ['1m', '5m', '15m']:
        try:
            patterns = engine.detect_patterns(candles, tf)
            results[tf] = {
                'total': len(patterns),
                'by_family': {},
                'examples': []
            }
            
            for p in patterns:
                family = p.family
                results[tf]['by_family'][family] = results[tf]['by_family'].get(family, 0) + 1
                
                if len(results[tf]['examples']) < 3:
                    results[tf]['examples'].append({
                        'family': p.family,
                        'name': p.name,
                        'direction': p.direction,
                        'strength': p.strength
                    })
            
            print(f"\n  ✅ {tf}: {len(patterns)} patterns detected")
            if patterns:
                for family, count in results[tf]['by_family'].items():
                    print(f"    - {family}: {count}")
        except Exception as e:
            print(f"  ❌ {tf}: ERROR - {e}")
            results[tf] = {'error': str(e)}
    
    # 3. Check what playbooks require
    print("\n3️⃣ PLAYBOOK REQUIREMENTS")
    
    from engines.playbook_loader import get_playbook_loader
    loader = get_playbook_loader()
    
    required_families = {}
    for playbook in loader.playbooks:
        families = playbook.required_pattern_families
        if families:
            required_families[playbook.name] = families
    
    print(f"  📋 Playbooks requiring candlestick patterns: {len(required_families)}/{len(loader.playbooks)}")
    
    # Check coverage
    all_detected_families = set()
    for tf_results in results.values():
        if 'by_family' in tf_results:
            all_detected_families.update(tf_results['by_family'].keys())
    
    all_required_families = set()
    for families in required_families.values():
        all_required_families.update(families)
    
    print(f"  🔍 Families detected: {sorted(all_detected_families)}")
    print(f"  📌 Families required: {sorted(all_required_families)}")
    
    missing = all_required_families - all_detected_families
    if missing:
        print(f"  ⚠️  Missing families: {sorted(missing)}")
    else:
        print(f"  ✅ All required families can be detected!")
    
    # 4. Export audit
    audit_report = {
        'month': month,
        'candlestick_engine_present': True,
        'candlestick_patterns_detected_total': sum(r.get('total', 0) for r in results.values()),
        'detection_by_timeframe': results,
        'required_by_playbook': required_families,
        'families_detected': sorted(all_detected_families),
        'families_required': sorted(all_required_families),
        'families_missing': sorted(missing),
        'coverage_pct': len(all_detected_families) / len(all_required_families) * 100 if all_required_families else 0
    }
    
    output_path = Path(fstr(results_path('candlestick_presence_audit_{month}.json')))
    with open(output_path, 'w') as f:
        json.dump(audit_report, f, indent=2)
    
    print(f"\n✅ Audit saved: {output_path}")
    
    # 5. Conclusion
    print("\n" + "="*70)
    print("CONCLUSION")
    print("="*70)
    
    total_detected = audit_report['candlestick_patterns_detected_total']
    
    if total_detected > 0:
        print(f"✅ Engine is FUNCTIONAL: {total_detected} patterns detected")
        print(f"✅ Coverage: {audit_report['coverage_pct']:.1f}% of required families")
        
        if missing:
            print(f"\n⚠️  RECOMMENDATION: Some required families are missing")
            print(f"   Options:")
            print(f"   1. Keep AGGRESSIVE bypass for missing families")
            print(f"   2. Adjust playbook requirements to use available families")
            print(f"   3. Enhance engine to detect missing patterns")
        else:
            print(f"\n✅ RECOMMENDATION: Engine can be wired into BacktestEngine")
            print(f"   Action: Call engine.detect_patterns() in _process_bar_optimized()")
            print(f"   Expected: Reduce candlestick_patterns bypass from 16 → ~0")
    else:
        print(f"❌ Engine detected 0 patterns on sample")
        print(f"   Possible reasons:")
        print(f"   1. Sample doesn't contain qualifying patterns")
        print(f"   2. Engine thresholds too strict")
        print(f"   3. Engine needs more data (larger lookback)")
        print(f"\n⚠️  KEEP bypass for now until engine produces patterns")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--month', default='2025-06')
    args = parser.parse_args()
    
    audit_candlestick_engine(args.month)
