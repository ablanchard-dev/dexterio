"""
P0.6.3 - Downloader 1m Extended (6 mois par fenêtres de 7 jours)

Stratégie:
- Télécharger par fenêtres de 7 jours (limite yfinance)
- Concat + tri + dedupe
- Quality gates stricts
- Rapport de qualité

Usage:
    python -m scripts.download_1m_extended --symbol SPY --from 2025-06-01 --to 2025-12-01
    python -m scripts.download_1m_extended --all --months 6
"""
import argparse
import json
import logging
import time
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np

from utils.path_resolver import historical_data_path

try:
    import yfinance as yf
except ImportError:
    raise ImportError("yfinance required: pip install yfinance")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION
# ============================================================================

DATA_DIR = historical_data_path("1m")
DATA_DIR.mkdir(parents=True, exist_ok=True)

SYMBOLS = ["SPY", "QQQ"]

# Limite yfinance: 7 jours par requête pour 1m
WINDOW_DAYS = 7

# Pause entre requêtes pour éviter rate limiting
REQUEST_DELAY_SECONDS = 2

# Quality gates
MAX_MISSING_BARS_PCT = 5.0  # Max 5% de barres manquantes par jour
MIN_BARS_PER_DAY = 360  # ~6h de trading (390 min session RTH)
RTH_START = "09:30"  # Regular Trading Hours start
RTH_END = "16:00"    # Regular Trading Hours end


# ============================================================================
# DOWNLOADER WINDOWED
# ============================================================================

def download_window(
    symbol: str,
    start_date: date,
    end_date: date,
    retries: int = 3
) -> Optional[pd.DataFrame]:
    """
    Télécharge une fenêtre de données 1m.
    
    Args:
        symbol: Ticker
        start_date: Date de début
        end_date: Date de fin
        retries: Nombre de tentatives
    
    Returns:
        DataFrame ou None si échec
    """
    for attempt in range(retries):
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(
                start=start_date.strftime('%Y-%m-%d'),
                end=end_date.strftime('%Y-%m-%d'),
                interval="1m"
            )
            
            if df.empty:
                logger.warning(f"  Fenêtre vide: {start_date} -> {end_date}")
                return None
            
            # Nettoyer
            df = df.reset_index()
            df.columns = [col.lower() for col in df.columns]
            
            # Renommer datetime
            if 'datetime' in df.columns:
                pass  # OK
            elif 'date' in df.columns:
                df = df.rename(columns={'date': 'datetime'})
            
            df['datetime'] = pd.to_datetime(df['datetime'])
            
            # Garder colonnes nécessaires
            required = ['datetime', 'open', 'high', 'low', 'close', 'volume']
            available = [c for c in required if c in df.columns]
            df = df[available]
            
            return df
            
        except Exception as e:
            logger.warning(f"  Tentative {attempt+1}/{retries} échouée: {e}")
            if attempt < retries - 1:
                time.sleep(REQUEST_DELAY_SECONDS * 2)
    
    return None


def download_extended(
    symbol: str,
    date_from: date,
    date_to: date,
    output_path: Optional[Path] = None,
) -> Tuple[Optional[pd.DataFrame], Dict[str, Any]]:
    """
    Télécharge des données 1m étendues par fenêtres de 7 jours.
    
    Args:
        symbol: Ticker
        date_from: Date de début
        date_to: Date de fin
        output_path: Chemin de sortie (optionnel)
    
    Returns:
        (DataFrame combiné, rapport de qualité)
    """
    logger.info(f"\n{'='*80}")
    logger.info(f"TÉLÉCHARGEMENT ÉTENDU: {symbol}")
    logger.info(f"Période: {date_from} -> {date_to}")
    logger.info(f"Fenêtres de {WINDOW_DAYS} jours")
    logger.info(f"{'='*80}")
    
    all_chunks: List[pd.DataFrame] = []
    windows_info: List[Dict[str, Any]] = []
    
    current_start = date_from
    window_num = 0
    
    while current_start < date_to:
        window_num += 1
        current_end = min(current_start + timedelta(days=WINDOW_DAYS), date_to)
        
        logger.info(f"\n📦 Fenêtre {window_num}: {current_start} -> {current_end}")
        
        df = download_window(symbol, current_start, current_end)
        
        window_info = {
            'window_num': window_num,
            'start': str(current_start),
            'end': str(current_end),
            'success': df is not None,
            'bars': len(df) if df is not None else 0,
        }
        
        if df is not None and len(df) > 0:
            logger.info(f"   ✅ {len(df)} barres téléchargées")
            all_chunks.append(df)
        else:
            logger.warning(f"   ❌ Échec ou vide")
        
        windows_info.append(window_info)
        
        # Pause pour éviter rate limiting
        time.sleep(REQUEST_DELAY_SECONDS)
        
        current_start = current_end
    
    # Combiner tous les chunks
    if not all_chunks:
        logger.error("Aucune donnée téléchargée!")
        return None, {'error': 'No data downloaded', 'windows': windows_info}
    
    logger.info(f"\n🔗 Combinaison de {len(all_chunks)} chunks...")
    
    combined = pd.concat(all_chunks, ignore_index=True)
    combined = combined.sort_values('datetime').reset_index(drop=True)
    
    # Dedupe par timestamp
    original_len = len(combined)
    combined = combined.drop_duplicates(subset=['datetime'], keep='last')
    duplicates_removed = original_len - len(combined)
    
    logger.info(f"   Total: {len(combined)} barres ({duplicates_removed} doublons supprimés)")
    logger.info(f"   Range: {combined['datetime'].min()} -> {combined['datetime'].max()}")
    
    # Quality gates
    quality_report = run_quality_gates(combined, symbol)
    quality_report['windows'] = windows_info
    quality_report['duplicates_removed'] = duplicates_removed
    
    # Sauvegarder si chemin fourni
    if output_path:
        combined.to_parquet(output_path, index=False)
        logger.info(f"\n💾 Sauvegardé: {output_path}")
        
        # Sauvegarder rapport qualité
        report_path = output_path.with_suffix('.quality.json')
        with open(report_path, 'w') as f:
            json.dump(quality_report, f, indent=2, default=str)
        logger.info(f"📊 Rapport: {report_path}")
    
    return combined, quality_report


# ============================================================================
# QUALITY GATES
# ============================================================================

def run_quality_gates(df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
    """
    Exécute les quality gates sur les données.
    
    Returns:
        Rapport de qualité
    """
    logger.info("\n🔍 QUALITY GATES")
    
    report = {
        'symbol': symbol,
        'total_bars': len(df),
        'date_range': {
            'start': str(df['datetime'].min()),
            'end': str(df['datetime'].max()),
        },
        'gates': {},
        'daily_stats': {},
        'rejected_days': [],
        'warnings': [],
        'passed': True,
    }
    
    # Gate 1: Timezone cohérent
    tz_values = df['datetime'].apply(lambda x: str(x.tzinfo) if x.tzinfo else 'naive').unique()
    gate_tz = len(tz_values) == 1
    report['gates']['timezone_consistent'] = {
        'passed': gate_tz,
        'values': list(tz_values),
    }
    if not gate_tz:
        report['warnings'].append(f"Multiple timezones detected: {tz_values}")
    
    # Gate 2: Pas de doublons timestamps
    duplicates = df['datetime'].duplicated().sum()
    gate_no_dups = duplicates == 0
    report['gates']['no_duplicate_timestamps'] = {
        'passed': gate_no_dups,
        'duplicates_found': int(duplicates),
    }
    
    # Gate 3: Colonnes OHLCV valides
    required_cols = ['datetime', 'open', 'high', 'low', 'close', 'volume']
    missing_cols = [c for c in required_cols if c not in df.columns]
    gate_cols = len(missing_cols) == 0
    report['gates']['required_columns'] = {
        'passed': gate_cols,
        'missing': missing_cols,
    }
    
    # Gate 4: Données OHLC valides
    if gate_cols:
        invalid_rows = (
            (df['high'] < df['low']) |
            (df['close'] > df['high']) |
            (df['close'] < df['low']) |
            (df['open'] > df['high']) |
            (df['open'] < df['low'])
        ).sum()
        gate_ohlc = invalid_rows == 0
        report['gates']['valid_ohlc'] = {
            'passed': gate_ohlc,
            'invalid_rows': int(invalid_rows),
        }
    
    # Gate 5: Analyse par jour
    df['date'] = df['datetime'].dt.date
    daily_stats = []
    
    for day, day_df in df.groupby('date'):
        # Filtrer RTH seulement
        day_df = day_df.copy()
        day_df['time'] = day_df['datetime'].dt.time
        
        # Compter les barres
        n_bars = len(day_df)
        
        # Calculer les barres attendues (390 min de session RTH)
        expected_bars = 390
        
        # Calculer le % manquant
        missing_pct = max(0, (expected_bars - n_bars) / expected_bars * 100)
        
        day_stat = {
            'date': str(day),
            'bars': n_bars,
            'expected': expected_bars,
            'missing_pct': round(missing_pct, 2),
            'rejected': missing_pct > MAX_MISSING_BARS_PCT,
        }
        daily_stats.append(day_stat)
        
        if day_stat['rejected']:
            report['rejected_days'].append(str(day))
    
    report['daily_stats'] = daily_stats
    
    # Gate 6: Jours valides
    valid_days = len([d for d in daily_stats if not d['rejected']])
    total_days = len(daily_stats)
    gate_days = valid_days >= total_days * 0.9  # Au moins 90% de jours valides
    
    report['gates']['sufficient_valid_days'] = {
        'passed': gate_days,
        'valid_days': valid_days,
        'total_days': total_days,
        'valid_pct': round(valid_days / total_days * 100, 1) if total_days > 0 else 0,
    }
    
    # Résumé
    all_gates_passed = all(g.get('passed', True) for g in report['gates'].values())
    report['passed'] = all_gates_passed
    
    # Log résumé
    logger.info(f"\n📋 RAPPORT QUALITÉ: {symbol}")
    logger.info(f"   Total barres: {report['total_bars']}")
    logger.info(f"   Jours valides: {valid_days}/{total_days}")
    logger.info(f"   Jours rejetés: {len(report['rejected_days'])}")
    logger.info(f"   Gates passés: {sum(1 for g in report['gates'].values() if g.get('passed', True))}/{len(report['gates'])}")
    
    if report['warnings']:
        logger.warning(f"   ⚠️ Warnings: {report['warnings']}")
    
    status = "✅ PASSED" if report['passed'] else "❌ FAILED"
    logger.info(f"   Status: {status}")
    
    return report


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="P0.6.3 - Downloader 1m Extended")
    parser.add_argument("--symbol", type=str, help="Symbole à télécharger (SPY, QQQ)")
    parser.add_argument("--from", dest="date_from", type=str, help="Date de début (YYYY-MM-DD)")
    parser.add_argument("--to", dest="date_to", type=str, help="Date de fin (YYYY-MM-DD)")
    parser.add_argument("--months", type=int, default=6, help="Nombre de mois à télécharger (défaut: 6)")
    parser.add_argument("--all", action="store_true", help="Télécharger tous les symboles")
    parser.add_argument("--output-dir", type=str, default=str(DATA_DIR), help="Répertoire de sortie")
    
    args = parser.parse_args()
    
    # Déterminer les dates
    if args.date_to:
        date_to = datetime.strptime(args.date_to, '%Y-%m-%d').date()
    else:
        date_to = datetime.now().date()
    
    if args.date_from:
        date_from = datetime.strptime(args.date_from, '%Y-%m-%d').date()
    else:
        date_from = date_to - timedelta(days=args.months * 30)
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Déterminer les symboles
    symbols = SYMBOLS if args.all else ([args.symbol] if args.symbol else SYMBOLS)
    
    logger.info(f"\n{'='*80}")
    logger.info("P0.6.3 - TÉLÉCHARGEMENT DONNÉES 1M ÉTENDUES")
    logger.info(f"{'='*80}")
    logger.info(f"Symboles: {symbols}")
    logger.info(f"Période: {date_from} -> {date_to}")
    logger.info(f"Sortie: {output_dir}")
    
    all_reports = {}
    
    for symbol in symbols:
        output_path = output_dir / f"{symbol.lower()}_1m_extended.parquet"
        
        df, report = download_extended(
            symbol=symbol,
            date_from=date_from,
            date_to=date_to,
            output_path=output_path,
        )
        
        all_reports[symbol] = report
    
    # Rapport consolidé
    consolidated_path = output_dir / "data_quality_report.json"
    with open(consolidated_path, 'w') as f:
        json.dump(all_reports, f, indent=2, default=str)
    
    logger.info(f"\n{'='*80}")
    logger.info("📊 RAPPORT CONSOLIDÉ")
    logger.info(f"{'='*80}")
    
    for symbol, report in all_reports.items():
        status = "✅" if report.get('passed', False) else "❌"
        bars = report.get('total_bars', 0)
        logger.info(f"  {status} {symbol}: {bars} barres")
    
    logger.info(f"\n📄 Rapport sauvegardé: {consolidated_path}")


if __name__ == "__main__":
    main()
