"""
Script de téléchargement de données historiques M1 pour backtesting
Stratégie : 30 derniers jours complets → découpage en blocs de 6 jours
"""
import yfinance as yf
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Créer les répertoires de données
DATA_DIR = Path("data/historical")
DATA_DIR_1M = DATA_DIR / "1m"
DATA_DIR_5M = DATA_DIR / "5m"

DATA_DIR_1M.mkdir(parents=True, exist_ok=True)
DATA_DIR_5M.mkdir(parents=True, exist_ok=True)

SYMBOLS = ["SPY", "QQQ"]


def download_last_n_days_1m(symbol: str, days: int = 7):
    """
    Télécharge les N derniers jours en 1 minute
    yfinance limite : maximum 7-8 jours par requête
    
    Args:
        symbol: Ticker (SPY ou QQQ)
        days: Nombre de jours (max 7 recommandé)
    
    Returns:
        DataFrame avec les données, ou None si échec
    """
    try:
        logger.info(f"📥 Téléchargement {symbol} : {days} derniers jours (1min)")
        
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=f"{days}d", interval="1m")
        
        if df.empty:
            logger.warning(f"Aucune donnée pour {symbol}")
            return None
        
        # Nettoyer les données
        df = df.reset_index()
        df.columns = [col.lower() for col in df.columns]
        
        # S'assurer que Datetime est bien datetime
        if 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'])
        elif 'date' in df.columns:
            df['datetime'] = pd.to_datetime(df['date'])
            df = df.drop('date', axis=1)
        
        # Colonnes nécessaires
        required_cols = ['datetime', 'open', 'high', 'low', 'close', 'volume']
        df = df[required_cols]
        
        # Trier par datetime
        df = df.sort_values('datetime').reset_index(drop=True)
        
        logger.info(f"✅ {symbol} : {len(df)} lignes")
        logger.info(f"   Période : {df['datetime'].min()} à {df['datetime'].max()}")
        
        return df
    
    except Exception as e:
        logger.error(f"❌ Erreur téléchargement {symbol} : {e}")
        return None


def download_multiple_7day_blocks(symbol: str, num_blocks: int = 4):
    """
    Télécharge plusieurs blocs de 7 jours en décalant dans le temps
    
    Stratégie : Télécharger les derniers 7j, puis 7j avant, etc.
    Limitation yfinance : on ne peut avoir que les 30 derniers jours total
    
    Args:
        symbol: Ticker
        num_blocks: Nombre de blocs de 7 jours à télécharger (max 4 pour 28 jours)
    
    Returns:
        List de DataFrames
    """
    all_dfs = []
    
    for i in range(num_blocks):
        # Calculer la période
        end_date = datetime.now() - timedelta(days=i*7)
        start_date = end_date - timedelta(days=7)
        
        logger.info(f"\n📦 Bloc {i+1}/{num_blocks} : {start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')}")
        
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(
                start=start_date.strftime('%Y-%m-%d'),
                end=end_date.strftime('%Y-%m-%d'),
                interval="1m"
            )
            
            if df.empty:
                logger.warning(f"   Bloc {i+1} vide")
                continue
            
            # Nettoyer
            df = df.reset_index()
            df.columns = [col.lower() for col in df.columns]
            
            if 'datetime' in df.columns:
                df['datetime'] = pd.to_datetime(df['datetime'])
            elif 'date' in df.columns:
                df['datetime'] = pd.to_datetime(df['date'])
                df = df.drop('date', axis=1)
            
            required_cols = ['datetime', 'open', 'high', 'low', 'close', 'volume']
            df = df[required_cols]
            df = df.sort_values('datetime').reset_index(drop=True)
            
            logger.info(f"   ✅ {len(df)} lignes : {df['datetime'].min()} → {df['datetime'].max()}")
            all_dfs.append(df)
        
        except Exception as e:
            logger.error(f"   ❌ Erreur bloc {i+1} : {e}")
            continue
    
    return all_dfs


def analyze_block_characteristics(df: pd.DataFrame, block_name: str):
    """
    Analyse les caractéristiques d'un bloc de données
    
    Returns:
        Dict avec métriques (volatilité, trend, range, etc.)
    """
    # Calculer ATR (Average True Range) simplifié
    df['tr'] = df[['high', 'low']].apply(lambda x: x['high'] - x['low'], axis=1)
    atr = df['tr'].mean()
    
    # Calculer le range total
    price_range = df['high'].max() - df['low'].min()
    
    # Calculer le mouvement directionnel
    first_close = df['close'].iloc[0]
    last_close = df['close'].iloc[-1]
    directional_move = last_close - first_close
    directional_pct = (directional_move / first_close) * 100
    
    # Détecter trend vs range
    # Si le prix bouge plus de 2% de manière directionnelle = trend
    # Sinon = range/chop
    is_trend = abs(directional_pct) > 2.0
    trend_type = "uptrend" if directional_pct > 0 else "downtrend" if directional_pct < 0 else "neutral"
    
    # Volatilité relative (ATR / prix moyen)
    avg_price = df['close'].mean()
    volatility_pct = (atr / avg_price) * 100
    
    return {
        'name': block_name,
        'start': df['datetime'].min(),
        'end': df['datetime'].max(),
        'bars': len(df),
        'atr': round(atr, 2),
        'volatility_pct': round(volatility_pct, 3),
        'price_range': round(price_range, 2),
        'directional_move': round(directional_move, 2),
        'directional_pct': round(directional_pct, 2),
        'is_trend': is_trend,
        'trend_type': trend_type,
        'first_close': round(first_close, 2),
        'last_close': round(last_close, 2)
    }


def split_into_6day_blocks(df: pd.DataFrame, symbol: str):
    """
    Découpe un DataFrame en blocs de 6 jours de trading consécutifs
    
    Args:
        df: DataFrame avec colonnes datetime, open, high, low, close, volume
        symbol: Ticker (pour nommage des fichiers)
    
    Returns:
        List de dicts avec info sur chaque bloc
    """
    logger.info(f"\n🔪 Découpage en blocs de 6 jours pour {symbol}")
    
    # Grouper par jour
    df['date'] = df['datetime'].dt.date
    days = df['date'].unique()
    
    logger.info(f"   Total jours de trading : {len(days)}")
    
    # Créer des blocs de 6 jours consécutifs
    blocks = []
    block_num = 1
    
    for i in range(0, len(days), 6):
        block_days = days[i:i+6]
        
        if len(block_days) < 5:  # On veut au moins 5 jours
            logger.info(f"   Bloc {block_num} ignoré (seulement {len(block_days)} jours)")
            continue
        
        # Extraire les données de ce bloc
        block_df = df[df['date'].isin(block_days)].copy()
        block_df = block_df.drop('date', axis=1)
        
        # Nom du bloc
        start_date = block_df['datetime'].min().strftime('%Y%m%d')
        end_date = block_df['datetime'].max().strftime('%Y%m%d')
        block_name = f"block{block_num}_{start_date}_{end_date}"
        
        # Analyser les caractéristiques
        characteristics = analyze_block_characteristics(block_df, block_name)
        
        # Sauvegarder le bloc
        filename = f"{symbol.lower()}_1m_{block_name}.parquet"
        filepath = DATA_DIR_1M / filename
        block_df.to_parquet(filepath, index=False)
        
        blocks.append({
            'symbol': symbol,
            'block_num': block_num,
            'filename': filename,
            'filepath': str(filepath),
            **characteristics
        })
        
        logger.info(f"   ✅ Bloc {block_num} : {start_date} → {end_date}")
        logger.info(f"      Bars: {len(block_df)}, Type: {characteristics['trend_type']}, Vol: {characteristics['volatility_pct']:.3f}%")
        
        block_num += 1
    
    return blocks


def download_and_split_all():
    """
    Télécharge plusieurs blocs de 7 jours en 1min pour SPY et QQQ
    Puis les découpe en blocs de 6 jours utilisables pour backtest
    """
    logger.info("="*80)
    logger.info("TÉLÉCHARGEMENT DONNÉES M1 - STRATÉGIE MULTI-BLOCS 7 JOURS")
    logger.info("="*80)
    logger.info("Limite yfinance : 7-8 jours max par requête")
    logger.info("Solution : Télécharger 4 blocs de 7 jours (28 jours total)")
    logger.info("="*80)
    
    all_blocks = []
    
    for symbol in SYMBOLS:
        logger.info(f"\n{'='*80}")
        logger.info(f"SYMBOLE : {symbol}")
        logger.info(f"{'='*80}")
        
        # Télécharger 4 blocs de 7 jours
        dfs = download_multiple_7day_blocks(symbol, num_blocks=4)
        
        if not dfs:
            logger.error(f"❌ Aucune donnée pour {symbol}")
            continue
        
        # Combiner tous les blocs
        logger.info(f"\n🔗 Combinaison de {len(dfs)} blocs...")
        combined_df = pd.concat(dfs, ignore_index=True)
        combined_df = combined_df.sort_values('datetime').reset_index(drop=True)
        
        # Supprimer les doublons éventuels
        combined_df = combined_df.drop_duplicates(subset=['datetime'], keep='first')
        
        logger.info(f"✅ Total combiné : {len(combined_df)} lignes")
        logger.info(f"   Période : {combined_df['datetime'].min()} → {combined_df['datetime'].max()}")
        
        # Sauvegarder le fichier combiné
        filename = f"{symbol.lower()}_1m_combined.parquet"
        filepath = DATA_DIR_1M / filename
        combined_df.to_parquet(filepath, index=False)
        logger.info(f"   Sauvegardé : {filepath}")
        
        # Découper en blocs de 6 jours
        blocks = split_into_6day_blocks(combined_df, symbol)
        all_blocks.extend(blocks)
    
    return all_blocks


def verify_data_integrity():
    """Vérifie l'intégrité des données téléchargées"""
    logger.info("\n" + "="*80)
    logger.info("VÉRIFICATION DE L'INTÉGRITÉ DES DONNÉES")
    logger.info("="*80)
    
    files = sorted(DATA_DIR_1M.glob("*.parquet"))
    
    # Exclure le fichier de résumé
    files = [f for f in files if 'summary' not in f.name]
    
    if not files:
        logger.error("❌ Aucun fichier trouvé !")
        return False
    
    all_ok = True
    
    for filepath in files:
        try:
            df = pd.read_parquet(filepath)
            
            # Vérifications
            checks = {
                "Non vide": len(df) > 0,
                "Colonnes OK": all(col in df.columns for col in ['datetime', 'open', 'high', 'low', 'close', 'volume']),
                "Pas de NaN": not df[['open', 'high', 'low', 'close']].isnull().any().any(),
                "High >= Low": (df['high'] >= df['low']).all(),
                "Close dans range": ((df['close'] >= df['low']) & (df['close'] <= df['high'])).all()
            }
            
            all_checks_passed = all(checks.values())
            
            status = "✅" if all_checks_passed else "❌"
            
            if not all_checks_passed:
                logger.info(f"{status} {filepath.name}")
                for check_name, passed in checks.items():
                    if not passed:
                        logger.warning(f"   ⚠ {check_name} : ÉCHEC")
                all_ok = False
        
        except Exception as e:
            logger.error(f"❌ Erreur lecture {filepath.name} : {e}")
            all_ok = False
    
    return all_ok


def generate_blocks_summary(blocks):
    """Génère un résumé des blocs téléchargés"""
    if not blocks:
        logger.error("Aucun bloc créé")
        return
    
    logger.info("\n" + "="*80)
    logger.info("📊 RÉSUMÉ DES BLOCS CRÉÉS")
    logger.info("="*80)
    
    # Grouper par symbole
    spy_blocks = [b for b in blocks if b['symbol'] == 'SPY']
    qqq_blocks = [b for b in blocks if b['symbol'] == 'QQQ']
    
    logger.info(f"\nSPY : {len(spy_blocks)} blocs")
    logger.info(f"QQQ : {len(qqq_blocks)} blocs")
    
    # Analyser les contextes
    logger.info("\n" + "="*80)
    logger.info("🎯 ANALYSE DES CONTEXTES")
    logger.info("="*80)
    
    for symbol in ['SPY', 'QQQ']:
        symbol_blocks = [b for b in blocks if b['symbol'] == symbol]
        
        if not symbol_blocks:
            continue
        
        logger.info(f"\n{symbol}:")
        
        # Compter les types
        trends = [b for b in symbol_blocks if b['is_trend']]
        ranges = [b for b in symbol_blocks if not b['is_trend']]
        uptrends = [b for b in symbol_blocks if b['trend_type'] == 'uptrend']
        downtrends = [b for b in symbol_blocks if b['trend_type'] == 'downtrend']
        
        logger.info(f"  Trends : {len(trends)} ({len(uptrends)} up, {len(downtrends)} down)")
        logger.info(f"  Ranges : {len(ranges)}")
        
        # Volatilité moyenne
        avg_vol = np.mean([b['volatility_pct'] for b in symbol_blocks])
        logger.info(f"  Volatilité moyenne : {avg_vol:.3f}%")
        
        # Lister les blocs
        logger.info(f"\n  Détail des blocs :")
        for b in symbol_blocks:
            context = f"{b['trend_type']}" if b['is_trend'] else "range/chop"
            logger.info(f"    • {b['name']}: {context}, vol={b['volatility_pct']:.3f}%, move={b['directional_pct']:+.2f}%")
    
    # Sauvegarder un CSV de résumé
    df_summary = pd.DataFrame(blocks)
    summary_path = DATA_DIR_1M / "blocks_summary.csv"
    df_summary.to_csv(summary_path, index=False)
    logger.info(f"\n📄 Résumé sauvegardé : {summary_path}")


if __name__ == "__main__":
    # Télécharger et découper
    blocks = download_and_split_all()
    
    if blocks:
        # Vérifier l'intégrité
        integrity_ok = verify_data_integrity()
        
        # Générer le résumé
        generate_blocks_summary(blocks)
        
        if integrity_ok:
            logger.info("\n" + "="*80)
            logger.info("🎉 TÉLÉCHARGEMENT ET DÉCOUPAGE TERMINÉS AVEC SUCCÈS !")
            logger.info("="*80)
            logger.info(f"\n📂 Fichiers dans : {DATA_DIR_1M}")
            logger.info(f"   Total blocs : {len(blocks)}")
        else:
            logger.error("\n⚠ Téléchargement terminé mais des problèmes d'intégrité détectés")
    else:
        logger.error("\n❌ Échec du téléchargement")
