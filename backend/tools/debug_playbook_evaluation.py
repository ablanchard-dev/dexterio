#!/usr/bin/env python3
"""
Debug pourquoi evaluate_all_playbooks ne retourne aucun match
"""
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter

sys.path.insert(0, str(Path(__file__).parent.parent))

# Activer logging debug
logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from engines.playbook_loader import get_playbook_loader, PlaybookEvaluator
from engines.patterns.custom_detectors import detect_custom_patterns
from engines.market_state import MarketStateEngine
from models.market_data import Candle
from config.settings import settings
import pandas as pd

def debug_evaluation_simple():
    """
    Simule une évaluation de playbook sur un petit échantillon de données
    """
    print("\n🔍 DEBUG: Évaluation des playbooks")
    print("=" * 70)
    
    # Charger les playbooks
    loader = get_playbook_loader()
    evaluator = PlaybookEvaluator(loader)
    
    trading_mode = settings.TRADING_MODE
    playbooks = loader.get_playbooks_for_mode(trading_mode)
    
    print(f"Mode: {trading_mode}")
    print(f"Playbooks chargés: {len(playbooks)}")
    for pb in playbooks[:5]:
        print(f"  - {pb.name} ({pb.category})")
    print()
    
    # Charger données 1m SPY pour juin 2025
    data_path = Path(str(historical_data_path('1m')) + '/SPY.parquet')
    df = pd.read_parquet(data_path)
    
    if 'datetime' not in df.columns:
        df = df.reset_index()
    
    df['datetime'] = pd.to_datetime(df['datetime'], utc=True)
    
    # Filtrer juin 2025
    start = pd.Timestamp('2025-06-01', tz='UTC')
    end = pd.Timestamp('2025-07-01', tz='UTC')
    df_june = df[(df['datetime'] >= start) & (df['datetime'] < end)]
    
    print(f"📊 Données chargées: {len(df_june)} bars pour juin 2025")
    
    # Prendre une petite fenêtre pendant la session NY (09:30-16:00 ET)
    # 2025-06-10 09:45 ET = 2025-06-10 13:45 UTC
    # Chercher des bars autour de 14:00 UTC (10:00 ET)
    df_june_sorted = df_june.sort_values('datetime')
    
    # Trouver l'index du premier timestamp >= 14:00 UTC le 10 juin
    target_time = pd.Timestamp('2025-06-10 14:00:00', tz='UTC')
    mask = df_june_sorted['datetime'] >= target_time
    if mask.any():
        start_idx = df_june_sorted[mask].index[0]
        # Prendre 100 bars à partir de cet index
        df_sample = df_june_sorted.loc[start_idx:start_idx+99]
    else:
        # Fallback: prendre au milieu
        df_sample = df_june.iloc[5000:5100]
    
    # Convertir en Candles
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
    
    print(f"📊 Échantillon: {len(candles_1m)} bougies 1m")
    print(f"  Premier timestamp: {candles_1m[0].timestamp}")
    print(f"  Dernier timestamp: {candles_1m[-1].timestamp}")
    print()
    
    # Détecter patterns ICT sur cet échantillon (simuler 5m)
    detections = detect_custom_patterns(candles_1m, "5m")
    ict_patterns = []
    for plist in detections.values():
        if plist:
            ict_patterns.extend(plist)
    
    print(f"🔍 Patterns ICT détectés: {len(ict_patterns)}")
    for p in ict_patterns[:5]:
        print(f"  - {p.pattern_type} {p.direction} @ {p.timeframe}")
    print()
    
    # Créer un market_state minimal
    market_state = {
        'bias': 'bullish',
        'current_session': 'NY',
        'daily_structure': 'bullish',
        'h4_structure': 'bullish',
        'h1_structure': 'bullish',
        'session_profile': {}
    }
    
    current_time = candles_1m[50].timestamp  # Milieu de la fenêtre
    
    print(f"🕐 Current time: {current_time}")
    print(f"📈 Market state: {market_state}")
    print()
    
    # Compteurs de rejets
    reject_stats = Counter()
    
    # Évaluer chaque playbook manuellement pour voir les rejets
    print("🎯 Évaluation détaillée des playbooks:")
    print("-" * 70)
    
    for playbook in playbooks[:10]:  # Top 10
        print(f"\n📋 Playbook: {playbook.name}")
        print(f"   Required signals: {getattr(playbook, 'required_signals', [])}")
        print(f"   ICT confluences:")
        print(f"      require_sweep: {getattr(playbook, 'require_sweep', False)}")
        print(f"      require_bos: {getattr(playbook, 'require_bos', False)}")
        print(f"      allow_fvg: {getattr(playbook, 'allow_fvg', False)}")
        
        basic_pass, basic_reason = evaluator._check_basic_filters(
            playbook, 'SPY', current_time, market_state
        )
        
        if not basic_pass:
            print(f"   ❌ Rejet: {basic_reason}")
            reject_stats[f"basic_filter:{basic_reason}"] += 1
            continue
        
        # Vérifier manuellement les patterns requis
        has_sweep = any(p.pattern_type == 'sweep' for p in ict_patterns)
        has_fvg = any(p.pattern_type == 'fvg' for p in ict_patterns)
        has_bos = any(p.pattern_type == 'bos' for p in ict_patterns)
        
        print(f"   Patterns détectés: sweep={has_sweep}, fvg={has_fvg}, bos={has_bos}")
        print(f"   Total ICT patterns: {len(ict_patterns)}")
        
        score, details = evaluator._evaluate_playbook_conditions(
            playbook,
            market_state,
            ict_patterns,
            []  # candle_patterns
        )
        
        if score is None:
            print(f"   ❌ Rejet: score=None (conditions non remplies)")
            # Identifier la raison probable
            if len(ict_patterns) == 0:
                print(f"      Raison probable: Aucun pattern ICT détecté")
            else:
                print(f"      Raison probable: Confluences ICT non satisfaites ou patterns candlestick manquants")
                print(f"      Patterns disponibles:")
                for p in ict_patterns:
                    print(f"        - {p.pattern_type} {p.direction} @ {p.timeframe}")
            reject_stats["score_none"] += 1
            continue
        
        grade = evaluator._calculate_grade(score, playbook.grade_thresholds)
        
        print(f"   ✅ MATCH! Score: {score:.2f}, Grade: {grade}")
        reject_stats["matched"] += 1
    
    print()
    print("📊 RÉSUMÉ DES REJETS:")
    print("-" * 70)
    for reason, count in reject_stats.most_common():
        print(f"  {reason}: {count}")
    
    # Sauvegarder rapport
    output_path = Path(str(results_path('playbook_evaluation_debug.json')))
    with open(output_path, 'w') as f:
        json.dump({
            'trading_mode': trading_mode,
            'total_playbooks': len(playbooks),
            'sample_size': len(candles_1m),
            'ict_patterns_detected': len(ict_patterns),
            'current_time': str(current_time),
            'market_state': market_state,
            'reject_stats': dict(reject_stats)
        }, f, indent=2)
    
    print(f"\n✅ Rapport sauvegardé: {output_path}")

if __name__ == '__main__':
    debug_evaluation_simple()
