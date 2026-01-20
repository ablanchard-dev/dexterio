"""
P2 Phase 0 - Baseline Non-Regression Generator

Ce script génère des baselines de référence AVANT tout patch P2.
But: prouver "zéro régression" après chaque changement.

Baselines générées:
- baseline_1d.json: 1 jour fixe (2025-06-03)
- baseline_5d.json: 5 jours fixes (2025-06-03 → 2025-06-09)

Métriques collectées:
- setups_total, playbook_matches_total, matched_count
- trades_count, total_R, PF, expectancy_R, maxDD_R
- top_rejections_by_reason (top 20)
- equity + trades (Parquet/CSV)
"""
import sys
from pathlib import Path
from datetime import datetime
import json
import logging

# Bootstrap path
_current_file = Path(__file__).resolve()
_backend_dir = _current_file.parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from models.backtest import BacktestConfig
from backtest.engine import BacktestEngine
from backtest.metrics import calculate_metrics
from config.settings import settings

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def generate_baseline(
    name: str,
    start_date: str,
    end_date: str,
    symbols: list = None,
    mode: str = "AGGRESSIVE"
) -> dict:
    """
    Génère une baseline pour une période donnée.
    
    Args:
        name: Nom du run (ex: "1d", "5d")
        start_date: Date début YYYY-MM-DD
        end_date: Date fin YYYY-MM-DD
        symbols: Liste symboles (default: ["SPY"])
        mode: Trading mode (default: "AGGRESSIVE")
    
    Returns:
        Dict avec métriques + metadata
    """
    symbols = symbols or ["SPY"]  # Default SPY only for speed
    
    logger.info(f"📊 Generating baseline '{name}': {start_date} → {end_date}")
    
    # Config backtest
    config = BacktestConfig(
        run_name=f"baseline_{name}",
        symbols=symbols,
        data_paths=[fstr(historical_data_path('1m')) + '/{sym}.parquet' for sym in symbols],
        initial_capital=settings.INITIAL_CAPITAL,
        trading_mode=mode,
        trade_types=['DAILY', 'SCALP'],
        output_dir=str(results_path()),
        # Date slicing (sera implémenté en Phase 1)
        # start_date=start_date,
        # end_date=end_date
    )
    
    # Run backtest
    engine = BacktestEngine(config)
    engine.load_data()
    
    # WORKAROUND: Filter data manually (date slicing pas encore implémenté)
    # On filtrera le combined_data directement via datetime masking
    if engine.combined_data is not None and 'datetime' in engine.combined_data.columns:
        import pandas as pd
        original_size = len(engine.combined_data)
        
        # Convertir dates en datetime si nécessaire
        engine.combined_data['datetime'] = pd.to_datetime(engine.combined_data['datetime'])
        
        # Filter by date range
        mask = (
            (engine.combined_data['datetime'].dt.date >= pd.to_datetime(start_date).date()) &
            (engine.combined_data['datetime'].dt.date <= pd.to_datetime(end_date).date())
        )
        engine.combined_data = engine.combined_data[mask].copy()
        filtered_size = len(engine.combined_data)
        logger.info(f"  Filtered data: {original_size} → {filtered_size} bars ({start_date} to {end_date})")
    
    result = engine.run()
    
    # Collecter métriques
    setups_generated = len(getattr(engine, 'all_generated_setups', []))
    
    # Playbook matches
    playbook_matches = []
    for setup in getattr(engine, 'all_generated_setups', []):
        if setup.playbook_matches:
            playbook_matches.extend(setup.playbook_matches)
    
    # Trades
    trades_data = []
    for trade in engine.trades:
        trades_data.append({
            "trade_id": trade.trade_id,
            "symbol": trade.symbol,
            "playbook": trade.playbook,
            "entry_price": trade.entry_price,
            "exit_price": trade.exit_price,
            "pnl_dollars": trade.pnl_dollars,
            "risk_dollars": trade.risk_dollars,
            "r_multiple": trade.r_multiple,
            "pnl_R_account": trade.pnl_R_account,
            "outcome": trade.outcome,
            "exit_reason": trade.exit_reason,
            "date": trade.timestamp_entry.strftime('%Y-%m-%d') if trade.timestamp_entry else None,
            "month": trade.timestamp_entry.strftime('%Y-%m') if trade.timestamp_entry else None,
        })
    
    # Calculer métriques via metrics.py (formules verrouillées)
    metrics = calculate_metrics(trades_data) if trades_data else {}
    
    # Top rejections (depuis PlaybookEvaluator stats)
    # Note: À ce stade, on n'a pas encore instrumenté les rejections complètes
    # On va extraire ce qu'on peut de playbook_loader
    from engines.playbook_loader import get_playbook_loader
    loader = get_playbook_loader()
    
    # Stats de rejections (placeholder - sera enrichi après instrumentation)
    top_rejections = {}
    
    # Construire baseline dict
    baseline = {
        "name": name,
        "timestamp": datetime.utcnow().isoformat(),
        "config": {
            "start_date": start_date,
            "end_date": end_date,
            "symbols": symbols,
            "mode": mode,
            "trade_types": config.trade_types,
        },
        "data": {
            "bars_processed": result.total_bars,
            "date_range_actual": f"{result.start_date} → {result.end_date}",
        },
        "funnel": {
            "setups_total": setups_generated,
            "playbook_matches_total": len(playbook_matches),
            "matched_count": len(set(m.playbook_name for m in playbook_matches)),
        },
        "trades": {
            "trades_count": len(trades_data),
            "total_R": metrics.get("total_r", 0.0),
            "profit_factor": metrics.get("profit_factor", 0.0),
            "expectancy_R": metrics.get("expectancy_r", 0.0),
            "max_drawdown_R": metrics.get("max_drawdown_r", 0.0),
            "winrate": metrics.get("winrate", 0.0),
            "wins": metrics.get("wins", 0),
            "losses": metrics.get("losses", 0),
            "breakevens": metrics.get("breakevens", 0),
        },
        "top_rejections": top_rejections,
    }
    
    return baseline


def main():
    """Génère les baselines 1d + 5d (SPY ONLY pour rapidité)"""
    
    logger.info("=" * 80)
    logger.info("PHASE 0 - BASELINE NON-REGRESSION")
    logger.info("=" * 80)
    logger.info("NOTE: Using SPY only for speed optimization")
    
    results_dir = Path(str(results_path()))
    results_dir.mkdir(parents=True, exist_ok=True)
    
    # Baseline 1 jour: 2025-06-03 (mardi) - SPY ONLY
    baseline_1d = generate_baseline(
        name="1d",
        start_date="2025-06-03",
        end_date="2025-06-03",
        symbols=["SPY"]  # SPY ONLY for speed
    )
    
    # Sauvegarder baseline_1d
    path_1d = results_dir / "baseline_1d.json"
    with open(path_1d, 'w', encoding='utf-8') as f:
        json.dump(baseline_1d, f, indent=2)
    logger.info(f"✅ Saved: {path_1d}")
    
    # Baseline 5 jours: 2025-06-03 → 2025-06-09 (Tue-Mon, 1 semaine complète) - SPY ONLY
    baseline_5d = generate_baseline(
        name="5d",
        start_date="2025-06-03",
        end_date="2025-06-09",
        symbols=["SPY"]  # SPY ONLY for speed
    )
    
    # Sauvegarder baseline_5d
    path_5d = results_dir / "baseline_5d.json"
    with open(path_5d, 'w', encoding='utf-8') as f:
        json.dump(baseline_5d, f, indent=2)
    logger.info(f"✅ Saved: {path_5d}")
    
    # Résumé
    logger.info("\n" + "=" * 80)
    logger.info("BASELINE SUMMARY")
    logger.info("=" * 80)
    
    logger.info("\n📊 1-Day Baseline (2025-06-03):")
    logger.info(f"  Bars: {baseline_1d['data']['bars_processed']}")
    logger.info(f"  Setups: {baseline_1d['funnel']['setups_total']}")
    logger.info(f"  Playbook matches: {baseline_1d['funnel']['playbook_matches_total']}")
    logger.info(f"  Trades: {baseline_1d['trades']['trades_count']}")
    logger.info(f"  Total R: {baseline_1d['trades']['total_R']:.3f}")
    logger.info(f"  PF: {baseline_1d['trades']['profit_factor']:.2f}")
    logger.info(f"  Expectancy R: {baseline_1d['trades']['expectancy_R']:.3f}")
    
    logger.info("\n📊 5-Day Baseline (2025-06-03 → 2025-06-09):")
    logger.info(f"  Bars: {baseline_5d['data']['bars_processed']}")
    logger.info(f"  Setups: {baseline_5d['funnel']['setups_total']}")
    logger.info(f"  Playbook matches: {baseline_5d['funnel']['playbook_matches_total']}")
    logger.info(f"  Trades: {baseline_5d['trades']['trades_count']}")
    logger.info(f"  Total R: {baseline_5d['trades']['total_R']:.3f}")
    logger.info(f"  PF: {baseline_5d['trades']['profit_factor']:.2f}")
    logger.info(f"  Expectancy R: {baseline_5d['trades']['expectancy_R']:.3f}")
    
    logger.info("\n" + "=" * 80)
    logger.info("✅ BASELINE GENERATION COMPLETE")
    logger.info("=" * 80)
    logger.info(f"\nArtifacts:")
    logger.info(f"  - {path_1d}")
    logger.info(f"  - {path_5d}")
    logger.info(f"\nCopy equity/trades from:")
    logger.info(f"  - /app/data/backtest_results/equity_baseline_1d_*.parquet")
    logger.info(f"  - /app/data/backtest_results/trades_baseline_1d_*.parquet")
    logger.info(f"  - /app/data/backtest_results/equity_baseline_5d_*.parquet")
    logger.info(f"  - /app/data/backtest_results/trades_baseline_5d_*.parquet")


if __name__ == "__main__":
    main()
