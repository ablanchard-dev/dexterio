#!/usr/bin/env python3
"""
Audit des signaux détectés par custom_detectors sur un mois donné
"""
import sys
import json
import argparse
import math
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from engines.patterns.custom_detectors import detect_custom_patterns
from models.market_data import Candle

def _to_py_float(x, default=0.0):
    """Convertit en float Python natif, gère NaN et None"""
    if x is None:
        return default
    try:
        if isinstance(x, float) and math.isnan(x):
            return default
        return float(x)
    except Exception:
        return default

def _to_py_int(x, default=0):
    """Convertit en int Python natif, gère NaN et None"""
    if x is None:
        return default
    try:
        if isinstance(x, float) and math.isnan(x):
            return default
        return int(x)
    except Exception:
        return default

def _to_timestamp(x):
    """Convertit en timestamp Python datetime (UTC naive)"""
    ts = pd.to_datetime(x, utc=True, errors="coerce")
    if ts is pd.NaT:
        raise ValueError(f"Invalid timestamp: {x}")
    # Retourne un datetime naive en UTC (pour compatibilité Pydantic)
    return ts.tz_convert("UTC").tz_localize(None)

def row_to_candle_dict(row: dict, symbol: str, timeframe: str):
    """Convertit une ligne DataFrame en dict propre pour Candle"""
    # Tolère différents noms de colonnes pour timestamp
    ts_raw = (
        row.get("ts") or row.get("timestamp") or row.get("time") or
        row.get("date") or row.get("datetime")
    )
    if ts_raw is None:
        raise ValueError(f"Missing timestamp column. Keys={list(row.keys())}")

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "timestamp": _to_timestamp(ts_raw),
        "open": _to_py_float(row.get("open") or row.get("o")),
        "high": _to_py_float(row.get("high") or row.get("h")),
        "low":  _to_py_float(row.get("low")  or row.get("l")),
        "close":_to_py_float(row.get("close")or row.get("c")),
        "volume": _to_py_int(row.get("volume") or row.get("v"), default=0),
    }

def audit_signals_month(month: str, symbols: list):
    """
    Audite les signaux détectés sur un mois
    
    Args:
        month: Format YYYY-MM
        symbols: Liste des symbols à auditer
    """
    results = {
        'month': month,
        'symbols': symbols,
        'signal_counts': {},
        'signal_examples': {}
    }
    
    for symbol in symbols:
        data_path = Path(fstr(historical_data_path('1m')) + '/{symbol}.parquet')
        if not data_path.exists():
            print(f"⚠️  {symbol}: data not found")
            continue
        
        # Charger données
        df = pd.read_parquet(data_path)
        if 'datetime' not in df.columns:
            df = df.reset_index()
        df['datetime'] = pd.to_datetime(df['datetime'], utc=True)
        
        # Filtrer mois
        year, mon = month.split('-')
        start = pd.Timestamp(f'{year}-{mon}-01', tz='UTC')
        if int(mon) == 12:
            end = pd.Timestamp(f'{int(year)+1}-01-01', tz='UTC')
        else:
            end = pd.Timestamp(f'{year}-{int(mon)+1:02d}-01', tz='UTC')
        
        df_month = df[(df['datetime'] >= start) & (df['datetime'] < end)]
        
        if len(df_month) == 0:
            print(f"⚠️  {symbol}: no data for {month}")
            continue
        
        print(f"\n🔍 {symbol}: {len(df_month)} bars ({month})")
        
        # Convertir en Candles avec gestion robuste des types
        candles_1m = []
        bad_rows = 0
        first_error = None
        
        for idx, row in df_month.iterrows():
            try:
                row_dict = row.to_dict()
                payload = row_to_candle_dict(row_dict, symbol=symbol, timeframe='1m')
                candle = Candle.model_validate(payload)
                candles_1m.append(candle)
            except Exception as e:
                bad_rows += 1
                if first_error is None:
                    first_error = {
                        "error": str(e),
                        "row_keys": list(row_dict.keys()),
                        "row_sample": {k: str(v) for k, v in list(row_dict.items())[:8]}
                    }
                continue
        
        # Détection signaux sur fenêtres glissantes
        signal_counts = defaultdict(int)
        signal_examples = defaultdict(list)
        
        # Parcourir par fenêtres de 100 bars (pour 5m, 15m reconstitués)
        window_size = 100
        for i in range(0, len(candles_1m), window_size):
            window = candles_1m[i:i+window_size]
            if len(window) < 10:
                continue
            
            # Détection sur TF simples (5m simulé)
            try:
                detections = detect_custom_patterns(window, "5m")
                
                for signal_type, patterns in detections.items():
                    if patterns:
                        signal_counts[signal_type] += len(patterns)
                        
                        # Sauvegarder exemples (max 2 par signal)
                        if len(signal_examples[signal_type]) < 2:
                            for p in patterns[:2]:
                                signal_examples[signal_type].append({
                                    'timestamp': str(p.timestamp),
                                    'zone_low': float(p.zone_low),
                                    'zone_high': float(p.zone_high),
                                    'timeframe': p.timeframe,
                                    'pattern_type': p.pattern_type
                                })
            except Exception as e:
                pass  # Silent pour ne pas spam
        
        print(f"  Total signals detected: {sum(signal_counts.values())}")
        for sig, count in sorted(signal_counts.items()):
            print(f"    {sig}: {count}")
        
        # Ajouter métrique de qualité des données
        results['signal_counts'][symbol] = {
            'raw_signals_total': sum(signal_counts.values()),
            'by_type': dict(signal_counts),
            'candle_build': {
                'total_rows': len(df_month),
                'valid_candles': len(candles_1m),
                'bad_rows': bad_rows,
                'first_error': first_error
            }
        }
        results['signal_examples'][symbol] = {k: v for k, v in signal_examples.items()}
    
    # Export JSON
    output_dir = Path(str(results_path()))
    output_dir.mkdir(exist_ok=True)
    
    counts_file = output_dir / f'signal_counts_{month}.json'
    examples_file = output_dir / f'signal_examples_{month}.json'
    
    with open(counts_file, 'w') as f:
        json.dump({
            'month': month,
            'symbols': symbols,
            'counts': results['signal_counts']
        }, f, indent=2)
    
    with open(examples_file, 'w') as f:
        json.dump({
            'month': month,
            'symbols': symbols,
            'examples': results['signal_examples']
        }, f, indent=2)
    
    print(f"\n✅ Exports:")
    print(f"   {counts_file}")
    print(f"   {examples_file}")
    
    return results

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--month', required=True, help='Format YYYY-MM')
    parser.add_argument('--symbols', nargs='+', default=['SPY', 'QQQ'])
    args = parser.parse_args()
    
    audit_signals_month(args.month, args.symbols)
