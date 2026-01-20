"""CLI runner pour le BacktestEngine (Phase 2.3)

Usage typique :
    python -m backend.backtest.run \
        --mode SAFE \
        --trade-type DAILY \
        --symbols SPY,QQQ
"""
import argparse
import logging
from pathlib import Path
from typing import List

from models.backtest import BacktestConfig
from backtest.engine import BacktestEngine
from utils.path_resolver import historical_data_path


logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="DexterioBOT Backtest Runner")

    parser.add_argument(
        "--mode",
        type=str,
        default="SAFE",
        choices=["SAFE", "AGGRESSIVE"],
        help="Mode de trading: SAFE ou AGGRESSIVE",
    )

    parser.add_argument(
        "--trade-type",
        type=str,
        default="BOTH",
        choices=["DAILY", "SCALP", "BOTH"],
        help="Type de trades à inclure",
    )

    parser.add_argument(
        "--symbols",
        type=str,
        default="SPY,QQQ",
        help="Liste de symboles séparés par des virgules (ex: SPY,QQQ)",
    )

    parser.add_argument(
        "--data-dir",
        type=str,
        default=None,  # Will use path_resolver default
        help="Répertoire contenant les fichiers Parquet M1",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Active un logging plus verbeux",
    )

    return parser.parse_args()


def discover_data_paths(data_dir: str = None, symbols: List[str] = None) -> List[str]:
    """Trouve les fichiers Parquet pertinents pour les symboles donnés"""
    # Use path_resolver if no explicit data_dir
    if data_dir is None:
        base = historical_data_path()
    else:
        base = Path(data_dir)
    
    if not base.exists():
        raise FileNotFoundError(f"Data directory not found: {base}")

    paths: List[str] = []
    for symbol in symbols:
        # P0.6.3: prefer single-file per symbol datasets (avoid mixing & duplicates)
        direct_upper = base / f"{symbol.upper()}.parquet"
        direct_lower = base / f"{symbol.lower()}.parquet"
        if direct_upper.exists():
            paths.append(str(direct_upper))
            continue
        if direct_lower.exists():
            paths.append(str(direct_lower))
            continue

        # Backward compat: legacy multi-file datasets
        pattern = f"{symbol.lower()}_1m_*.parquet"
        for p in base.glob(pattern):
            paths.append(str(p))

    if not paths:
        raise FileNotFoundError(f"Aucun fichier Parquet trouvé pour {symbols} dans {base}")

    return sorted(set(paths))


def main():
    args = parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]

    trade_types = ["DAILY", "SCALP"]
    if args.trade_type == "DAILY":
        trade_types = ["DAILY"]
    elif args.trade_type == "SCALP":
        trade_types = ["SCALP"]

    data_paths = discover_data_paths(args.data_dir, symbols)

    config = BacktestConfig(
        data_paths=data_paths,
        symbols=symbols,
        trading_mode=args.mode,
        trade_types=trade_types,
    )

    logger.info(
        "Lancement du backtest | mode=%s, trade_types=%s, symbols=%s, files=%d",
        config.trading_mode,
        config.trade_types,
        config.symbols,
        len(config.data_paths),
    )

    engine = BacktestEngine(config)
    result = engine.run()

    # Afficher un résumé synthétique en fin de run
    logger.info("\n===== BACKTEST SUMMARY =====")
    logger.info("Période: %s → %s", result.start_date, result.end_date)
    logger.info("Trades: %d | Winrate: %.1f%% | Expectancy: %.3fR | PF: %.2f",
                result.total_trades,
                result.winrate,
                result.expectancy_r,
                result.profit_factor,
                )
    logger.info("PnL: %.2fR | %.2f$ (%.2f%%)",
                result.total_pnl_r,
                result.total_pnl_dollars,
                result.total_pnl_pct,
                )


if __name__ == "__main__":
    main()
