"""
P0 - HTF PIPELINE DIAGNOSTIC
Test court (200 bars) pour diagnostiquer pourquoi les HTF arrivent vides au MarketStateEngine
"""
import sys
import logging
from pathlib import Path
import pandas as pd
from datetime import datetime

# Setup path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.path_resolver import backend_path, historical_data_path, results_path

_LOG_PATH = backend_path("logs", "p0_htf_diagnostic.log")
_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

# Configure logging pour capturer l'instrumentation
logging.basicConfig(
    level=logging.WARNING,  # WARNING pour voir les logs d'instrumentation
    format='%(levelname)s | %(name)s | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(str(_LOG_PATH), mode='w')
    ]
)

logger = logging.getLogger(__name__)

from models.backtest import BacktestConfig
from backtest.engine import BacktestEngine

def main():
    logger.info("=" * 80)
    logger.info("P0 HTF DIAGNOSTIC - Test court 200 bars")
    logger.info("=" * 80)
    
    # Charger seulement 200 bars pour diagnostic rapide
    data_path = historical_data_path("1m", "SPY.parquet")
    
    if not data_path.exists():
        logger.error(f"❌ Data file not found: {data_path}")
        return
    
    # Charger et limiter à 200 bars
    df_full = pd.read_parquet(data_path)
    
    # Support Parquet contract: datetime is in index
    if 'datetime' not in df_full.columns:
        df_full = df_full.reset_index()  # Convertir l'index en colonne
    
    df_full['datetime'] = pd.to_datetime(df_full['datetime'], utc=True, errors='coerce')
    df_full = df_full.sort_values('datetime').reset_index(drop=True)
    
    # Prendre 2000 bars à partir d'une date où il y a déjà de l'historique
    # (pour éviter le warmup initial)
    start_idx = 500  # Skip les premières 500 bars (warmup)
    df_test = df_full.iloc[start_idx:start_idx+2000].copy()
    
    # Sauvegarder temporairement
    temp_path = Path("/tmp/spy_200bars_diagnostic.parquet")
    df_test.to_parquet(temp_path)
    
    logger.info(f"✅ Test dataset: {len(df_test)} bars")
    logger.info(f"   Period: {df_test['datetime'].min()} → {df_test['datetime'].max()}")
    
    # Config backtest minimal
    config = BacktestConfig(
        data_paths=[str(temp_path)],
        symbols=['SPY'],
        start_date=df_test['datetime'].min(),
        end_date=df_test['datetime'].max(),
        initial_capital=100000.0,
        trading_mode='AGGRESSIVE',
        trade_types=['SCALP', 'DAILY'],
        output_dir=str(results_path()),
        run_name='p0_htf_diagnostic'
    )
    
    # Lancer le backtest
    logger.info("\n🚀 Starting diagnostic backtest...")
    engine = BacktestEngine(config)
    
    try:
        result = engine.run()
        
        logger.info("\n" + "=" * 80)
        logger.info("DIAGNOSTIC COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Total trades: {result.total_trades}")
        logger.info(f"Bars processed: {result.total_bars}")
        
        # Afficher un résumé des logs capturés
        log_file = _LOG_PATH
        if log_file.exists():
            with open(log_file, 'r') as f:
                lines = f.readlines()
                htf_checks = [l for l in lines if 'HTF PIPELINE CHECK' in l]
                htf_closes = [l for l in lines if 'HTF CLOSE DETECTED' in l]
                empty_errors = [l for l in lines if 'EMPTY ❌' in l]
                
                logger.info(f"\n📊 SUMMARY:")
                logger.info(f"  - HTF Pipeline checks: {len(htf_checks)}")
                logger.info(f"  - HTF Closes detected: {len(htf_closes)}")
                logger.info(f"  - Empty HTF warnings: {len(empty_errors)}")
                
                if empty_errors:
                    logger.error(f"\n🚨 PROBLEM DETECTED: HTF données vides trouvées!")
                    logger.error("   Affichage des 5 premières erreurs:")
                    for err in empty_errors[:5]:
                        logger.error(f"   {err.strip()}")
                else:
                    logger.info(f"\n✅ Pipeline HTF OK: Aucune donnée vide détectée")
        
    except Exception as e:
        logger.error(f"❌ Erreur lors du diagnostic: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    main()
