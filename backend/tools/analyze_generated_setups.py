#!/usr/bin/env python3
"""
Analyse rapide des setups générés par BacktestEngine
pour comprendre pourquoi matched_count=0 dans le funnel
"""
import sys
import json
from pathlib import Path
from collections import defaultdict, Counter

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.backtest import BacktestConfig
from backtest.engine import BacktestEngine
from config.settings import settings

def analyze_setups_fast(year_month: str):
    """
    Charge un backtest et analyse les premiers N setups pour diagnostic rapide
    """
    print(f"\n🔍 Diagnostic rapide des setups pour {year_month}")
    print("=" * 60)
    
    # Config backtest
    config = BacktestConfig(
        run_name=f'diagnostic_{year_month}',
        symbols=settings.SYMBOLS,
        data_paths=[fstr(historical_data_path('1m')) + '/{sym}.parquet' for sym in settings.SYMBOLS],
        initial_capital=settings.INITIAL_CAPITAL,
        trading_mode=settings.TRADING_MODE,
        trade_types=['DAILY', 'SCALP'],
        output_dir=str(results_path())
    )
    
    engine = BacktestEngine(config)
    engine.load_data()
    
    print(f"✅ Loaded {len(engine.combined_data)} bars")
    
    # Traiter seulement les 100 premières barres pour diagnostic rapide
    max_bars = 100
    bar_count = 0
    
    for idx, row in engine.combined_data.head(max_bars).iterrows():
        symbol = row['symbol']
        current_time = row['datetime']
        
        # Générer setup pour cette barre (même logique que BacktestEngine.run)
        setup = engine._process_bar(symbol, current_time)
        
        if setup:
            engine.all_generated_setups.append(setup)
        
        bar_count += 1
        
        if bar_count >= max_bars:
            break
    
    print(f"✅ Processed {bar_count} bars (fast mode)")
    print(f"📊 Generated {len(engine.all_generated_setups)} setups\n")
    
    if not engine.all_generated_setups:
        print("❌ Aucun setup généré. Le problème est dans le pipeline de génération.")
        return
    
    # Analyser le contenu des setups
    stats = {
        'total_setups': len(engine.all_generated_setups),
        'with_playbook_matches': 0,
        'without_playbook_matches': 0,
        'playbook_match_counts': Counter(),
        'quality_distribution': Counter(),
        'sample_setups': []
    }
    
    for setup in engine.all_generated_setups:
        if setup.playbook_matches:
            stats['with_playbook_matches'] += 1
            for match in setup.playbook_matches:
                stats['playbook_match_counts'][match.playbook_name] += 1
        else:
            stats['without_playbook_matches'] += 1
        
        stats['quality_distribution'][setup.quality] += 1
        
        # Garder 3 exemples
        if len(stats['sample_setups']) < 3:
            stats['sample_setups'].append({
                'timestamp': str(setup.timestamp),
                'symbol': setup.symbol,
                'quality': setup.quality,
                'final_score': setup.final_score,
                'playbook_matches': [
                    {
                        'name': m.playbook_name,
                        'confidence': m.confidence,
                        'matched_conditions': m.matched_conditions
                    }
                    for m in setup.playbook_matches
                ],
                'ict_patterns': len(setup.ict_patterns),
                'candlestick_patterns': len(setup.candlestick_patterns)
            })
    
    # Rapport
    print("📈 RÉSULTATS")
    print("-" * 60)
    print(f"Total setups générés: {stats['total_setups']}")
    print(f"  ✅ Avec playbook matches: {stats['with_playbook_matches']}")
    print(f"  ❌ Sans playbook matches: {stats['without_playbook_matches']}")
    print()
    
    if stats['playbook_match_counts']:
        print("🎯 Playbooks matchés (top 10):")
        for pb_name, count in stats['playbook_match_counts'].most_common(10):
            print(f"  {pb_name}: {count}")
    else:
        print("⚠️  AUCUN playbook matché !")
    
    print()
    print("📊 Distribution qualité:")
    for quality, count in sorted(stats['quality_distribution'].items()):
        print(f"  {quality}: {count}")
    
    # Sauvegarder diagnostic
    output_path = Path(str(results_path())) / f'setup_diagnostic_{year_month}.json'
    with open(output_path, 'w') as f:
        json.dump(stats, f, indent=2)
    
    print(f"\n✅ Diagnostic sauvegardé: {output_path}")
    
    # Afficher échantillons
    if stats['sample_setups']:
        print("\n📋 Échantillons de setups:")
        print("-" * 60)
        for i, sample in enumerate(stats['sample_setups'], 1):
            print(f"\nSetup #{i}:")
            print(f"  Timestamp: {sample['timestamp']}")
            print(f"  Symbol: {sample['symbol']}")
            print(f"  Quality: {sample['quality']}")
            print(f"  Score: {sample['final_score']:.2f}")
            print(f"  Playbook matches: {len(sample['playbook_matches'])}")
            if sample['playbook_matches']:
                for pm in sample['playbook_matches'][:2]:  # Max 2
                    print(f"    - {pm['name']} (conf: {pm['confidence']:.2f})")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--month', required=True, help='Format YYYY-MM')
    args = parser.parse_args()
    
    analyze_setups_fast(args.month)
