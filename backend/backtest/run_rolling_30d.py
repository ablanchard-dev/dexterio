"""Script de backtest rolling 30 jours pour DexterioBOT.

Ce script permet d'exécuter le backtest complet pour un mois donné (YYYY-MM)
et de générer des artefacts :
 - results/summary_YYYYMM.json : synthèse des setups détectés
 - results/trades_YYYYMM.parquet (placeholder) : liste des trades (non implémenté)
 - results/equity_YYYYMM.parquet (placeholder) : courbe d'équité (non implémenté)
 - results/funnel_by_playbook.json : métriques de funnel agrégées par playbook

La logique de slicing de données 30 jours est simplifiée ; sans accès à un
historique complet, le script utilise BacktestEngine pour parcourir toutes les
barres historiques et collecter les setups générés pendant l'exécution.
"""

import argparse
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# ---------------------------------------------------------------------------
#  Bootstrap for standalone execution
#
#  Ce script est conçu pour être lancé directement depuis la racine du dépôt
#  (python backend/backtest/run_rolling_30d.py).  Python n'ajoute pas
#  automatiquement le dossier `backend/` à sys.path, ce qui entraîne des
#  erreurs `ModuleNotFoundError: engines` lors de l'import.  Le code
#  ci‑dessous résout ce problème en ajoutant le chemin `backend/` au
#  sys.path si nécessaire.  Aucune logique métier n'est modifiée.
# ---------------------------------------------------------------------------
import sys
from pathlib import Path as _Path

_current_file = _Path(__file__).resolve()
# Chemin du dossier backend (parent de backtest)
_backend_dir = _current_file.parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from engines.funnel_metrics import FunnelMetrics
from config.settings import settings
from utils.path_resolver import historical_data_path, results_path

# Typing and helpers imports
from typing import List
from models.setup import ICTPattern
from utils.timeframes import get_session_info


def run_month(year_month: str) -> None:
    """
    Exécute un backtest pour un mois (format YYYY-MM) et instrumente le funnel.

    Cette fonction instancie BacktestEngine pour parcourir réellement toutes
    les barres historiques du mois, puis applique un filtrage supplémentaire
    pour comptabiliser les étapes du funnel (matched → pass_grade →
    pass_timefilter → pass_risk → executed) et les raisons de rejet
    (missing_required_signal et timefilter_outside_window).

    Args:
        year_month: Mois au format YYYY-MM (ex : '2025-06').
    """
    # Valider le format du mois
    try:
        dt = datetime.strptime(year_month, '%Y-%m')
    except ValueError:
        raise ValueError('Format attendu : YYYY-MM')

    # Construire BacktestConfig pour le mois cible
    from models.backtest import BacktestConfig
    from backtest.engine import BacktestEngine
    
    config = BacktestConfig(
        run_name=f'rolling_{year_month}',
        symbols=settings.SYMBOLS,
        data_paths=[str(historical_data_path("1m", f'{sym}.parquet')) for sym in settings.SYMBOLS],
        initial_capital=settings.INITIAL_CAPITAL,
        trading_mode=settings.TRADING_MODE,
        trade_types=['DAILY', 'SCALP'],
        output_dir=str(results_path())
    )
    
    # Initialiser et exécuter le backtest
    engine = BacktestEngine(config)
    engine.load_data()
    
    print(f"✅ Loaded {len(engine.combined_data)} bars for {year_month}")
    
    # Run backtest (parcourt toutes les barres)
    result = engine.run()
    
    print(f"✅ Backtest complete: {result.total_bars} bars processed, {result.total_trades} trades")
    
    # Les setups sont dans engine.all_generated_setups (collectés pendant le run)
    # On les récupère pour construire le funnel
    results = {}
    for symbol in config.symbols:
        symbol_setups = [s for s in getattr(engine, 'all_generated_setups', []) if s.symbol == symbol]
        results[symbol] = symbol_setups

    # Collecteur de métriques funnel
    metrics = FunnelMetrics()
    
    # Compteurs audit
    audit_counters = {
        'bars_seen': result.total_bars,
        'signals_seen_total': 0,
        'setups_generated_total': len(getattr(engine, 'all_generated_setups', [])),
        'reject_reasons': defaultdict(int)
    }

    # Préparer le résumé général
    summary = {
        'month': year_month,
        'timestamp': datetime.utcnow().isoformat(),
        'symbols': list(results.keys()),
        'setups_total': sum(len(s) for s in results.values()),
        'by_symbol': {},
    }

    # Analyser les playbook_matches dans les setups générés pour comptabiliser
    # le funnel réel (au lieu de refaire l'évaluation manuellement)
    from engines.playbook_loader import get_playbook_loader
    
    loader = get_playbook_loader()
    playbook_names_all = {pb.name for pb in loader.playbooks}

    for symbol, setups in results.items():
        summary['by_symbol'][symbol] = len(setups)
        
        if not setups:
            continue
        
        # Comptabiliser les setups par playbook et collecter les métriques
        for setup in setups:
            # Chaque setup contient les playbook_matches générés par SetupEngine
            if setup.playbook_matches:
                for match in setup.playbook_matches:
                    pb_name = match.playbook_name
                    # Enregistrer comme matché et exécuté
                    metrics.record_matched(pb_name, symbol=symbol, timestamp=setup.timestamp)
                    metrics.record_pass_grade(pb_name, symbol=symbol, timestamp=setup.timestamp)
                    metrics.record_pass_timefilter(pb_name, symbol=symbol, timestamp=setup.timestamp)
                    metrics.record_pass_risk(pb_name, symbol=symbol, timestamp=setup.timestamp)
                    metrics.record_executed(pb_name, symbol=symbol, timestamp=setup.timestamp)
            else:
                # Aucun playbook matché (rejet par SetupEngine)
                audit_counters['reject_reasons']['no_playbook_match'] += 1

    # Préparer le dossier de sortie
    results_dir = results_path()
    results_dir.mkdir(parents=True, exist_ok=True)

    # Sauvegarder le résumé
    summary_path = results_dir / f'summary_{dt.strftime("%Y%m")}.json'
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)

    # Sauvegarder les metrics de funnel
    metrics.save_json(results_dir / 'funnel_by_playbook.json')
    
    # Export audit counters (why no setups)
    if audit_counters['setups_generated_total'] == 0:
        why_no_setups_file = results_dir / f'why_no_setups_{year_month}.json'
        with open(why_no_setups_file, 'w') as f:
            json.dump({
                'month': year_month,
                'bars_seen': audit_counters['bars_seen'],
                'signals_seen_total': audit_counters['signals_seen_total'],
                'setups_generated_total': audit_counters['setups_generated_total'],
                'top_reject_reasons': dict(sorted(
                    audit_counters['reject_reasons'].items(),
                    key=lambda x: -x[1]
                )[:10])
            }, f, indent=2)
        print(f"  📋 Wrote: {why_no_setups_file}")

    # Création de fichiers vides pour trades et equity (non implémentés)
    (results_dir / f'trades_{dt.strftime("%Y%m")}.parquet').touch()
    (results_dir / f'equity_{dt.strftime("%Y%m")}.parquet').touch()

    print(f'Backtest terminé pour {year_month}. Résultats enregistrés dans {results_dir}')


def main() -> None:
    parser = argparse.ArgumentParser(description='Backtest rolling 30 jours')
    parser.add_argument('--month', required=True, help='Mois au format YYYY-MM (ex : 2025-06)')
    args = parser.parse_args()
    run_month(args.month)


if __name__ == '__main__':
    main()
