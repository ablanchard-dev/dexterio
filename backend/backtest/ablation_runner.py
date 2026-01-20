"""
P0.4 - Ablation Runner + Rapports Mensuels + Régime Tags

Ce runner permet d'exécuter des backtests avec différentes configurations de playbooks
et de générer des rapports comparatifs par fenêtre temporelle.

Usage:
    python -m backtest.ablation_runner --mode AGGRESSIVE --from 2025-11-01 --to 2025-12-01 --playbooks News_Fade
    python -m backtest.ablation_runner --ablation-all  # Lance les 6 scénarios standard
"""
import argparse
import json
import logging
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd

from backtest.engine import BacktestEngine, BacktestConfig
from backtest.metrics import (
    calculate_metrics,
    calculate_monthly_metrics,
    calculate_regime_metrics,
    export_trades_csv,
    export_daily_summary,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Reduce verbosity from engines during long multi-month runs (keeps logs usable)
logging.getLogger("engines").setLevel(logging.ERROR)
logging.getLogger("engines.risk_engine").setLevel(logging.ERROR)
logging.getLogger("backtest.engine").setLevel(logging.INFO)

logger = logging.getLogger(__name__)


# ============================================================================
# ABLATION SCENARIOS (standard 6 scénarios)
# ============================================================================

ABLATION_SCENARIOS = {
    "news_fade_only": {
        "name": "News_Fade seul",
        "playbooks": ["News_Fade"],
        "description": "Baseline News_Fade isolé"
    },
    "scalp_aplus_only": {
        "name": "SCALP_Aplus_1 seul",
        "playbooks": ["SCALP_Aplus_1_Mini_FVG_Retest_NY_Open"],
        "description": "A+ SCALP isolé"
    },
    "session_open_only": {
        "name": "Session_Open_Scalp seul",
        "playbooks": ["Session_Open_Scalp"],
        "description": "Session Open isolé"
    },
    "news_session": {
        "name": "News + Session",
        "playbooks": ["News_Fade", "Session_Open_Scalp"],
        "description": "Baseline historique ~+88R"
    },
    "news_session_scalp": {
        "name": "News + Session + SCALP A+",
        "playbooks": ["News_Fade", "Session_Open_Scalp", "SCALP_Aplus_1_Mini_FVG_Retest_NY_Open"],
        "description": "Combinaison complète AGGRESSIVE"
    },
    "day_aplus_only": {
        "name": "DAY_Aplus_1 seul",
        "playbooks": ["DAY_Aplus_1_Liquidity_Sweep_OB_Retest"],
        "description": "A+ DAY isolé (désactivé pour l'instant)"
    },
}


class AblationRunner:
    """
    Runner pour tests d'ablation avec rapports détaillés.
    """
    
    def __init__(
        self,
        mode: str = "AGGRESSIVE",
        symbols: List[str] = None,
        trade_types: List[str] = None,
        output_dir: str = None,
        data_dir: str = str(historical_data_path('1m')),
    ):
        self.mode = mode
        self.symbols = symbols or ["SPY", "QQQ"]
        self.trade_types = trade_types or ["DAILY", "SCALP"]
        self.output_dir = Path(output_dir or str(backtest_results_path('ablation')))
        self.data_dir = Path(data_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.results: Dict[str, Dict[str, Any]] = {}
    
    def run_scenario(
        self,
        scenario_id: str,
        playbooks: List[str],
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        description: str = "",
    ) -> Dict[str, Any]:
        """
        Exécute un scénario d'ablation.
        
        Args:
            scenario_id: Identifiant unique du scénario
            playbooks: Liste des playbooks à activer
            date_from: Date de début (YYYY-MM-DD)
            date_to: Date de fin (YYYY-MM-DD)
            description: Description du scénario
        
        Returns:
            Dict avec métriques et chemins des fichiers générés
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"ABLATION: {scenario_id} - {description}")
        logger.info(f"Playbooks: {playbooks}")
        logger.info(f"{'='*80}")
        
        # Créer un sous-dossier pour ce scénario
        scenario_dir = self.output_dir / scenario_id
        scenario_dir.mkdir(parents=True, exist_ok=True)
        
        # Configurer le backtest avec les playbooks spécifiques
        # Trouver les fichiers de données
        data_dir = self.data_dir

        # 1) Prefer single-file datasets if they exist for ALL requested symbols
        direct_paths = []
        for sym in self.symbols:
            p_upper = data_dir / f"{sym.upper()}.parquet"
            p_lower = data_dir / f"{sym.lower()}.parquet"
            if p_upper.exists():
                direct_paths.append(str(p_upper))
            elif p_lower.exists():
                direct_paths.append(str(p_lower))

        if len(direct_paths) == len(self.symbols) and len(direct_paths) > 0:
            data_paths = sorted(direct_paths)
        else:
            # 2) Fallback to legacy naming, per-symbol (avoid mixing unrelated parquets)
            data_paths = []
            for sym in self.symbols:
                pattern = f"{sym.lower()}_1m_*.parquet"
                data_paths.extend(str(p) for p in data_dir.glob(pattern))
            data_paths = sorted(data_paths)
        
        if not data_paths:
            raise ValueError(f"No data files found in {data_dir}")
        
        config = BacktestConfig(
            data_paths=data_paths,
            trading_mode=self.mode,
            symbols=self.symbols,
            trade_types=self.trade_types,
            output_dir=str(scenario_dir),
        )
        
        # Patcher temporairement l'allowlist du RiskEngine
        from engines.risk_engine import AGGRESSIVE_ALLOWLIST, AGGRESSIVE_DENYLIST
        original_allowlist = AGGRESSIVE_ALLOWLIST.copy()
        
        try:
            # Override allowlist pour ce scénario
            import engines.risk_engine as risk_module
            risk_module.AGGRESSIVE_ALLOWLIST = playbooks
            
            # Run backtest
            engine = BacktestEngine(config)
            result = engine.run()
            
            # Calculer les métriques détaillées
            trades_data = self._extract_trades_data(result, engine)
            metrics = calculate_metrics(trades_data, playbooks)
            monthly = calculate_monthly_metrics(trades_data)
            
            # Exporter les fichiers
            trades_csv_path = scenario_dir / f"trades_{scenario_id}.csv"
            export_trades_csv(trades_data, trades_csv_path)
            
            daily_path = scenario_dir / f"daily_summary_{scenario_id}.json"
            export_daily_summary(trades_data, daily_path)
            
            report_path = scenario_dir / f"report_{scenario_id}.json"
            report = {
                "scenario_id": scenario_id,
                "description": description,
                "playbooks": playbooks,
                "date_from": date_from,
                "date_to": date_to,
                "mode": self.mode,
                "symbols": self.symbols,
                "global_metrics": metrics,
                "monthly_metrics": monthly,
                "files": {
                    "trades_csv": str(trades_csv_path),
                    "daily_summary": str(daily_path),
                    "report": str(report_path),
                }
            }
            
            with report_path.open("w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, default=str)
            
            self.results[scenario_id] = report
            
            logger.info(f"\n📊 Scénario {scenario_id} terminé:")
            logger.info(f"   Total R: {metrics['total_r']:.2f}")
            logger.info(f"   Trades: {metrics['total_trades']}")
            logger.info(f"   WR: {metrics['winrate']:.1f}%")
            logger.info(f"   PF: {metrics['profit_factor']:.2f}")
            logger.info(f"   MaxDD: {metrics['max_drawdown_r']:.2f}R")
            
            return report
            
        finally:
            # Restaurer l'allowlist originale
            risk_module.AGGRESSIVE_ALLOWLIST = original_allowlist
    
    def _extract_trades_data(self, result, engine) -> List[Dict[str, Any]]:
        """Extrait les données de trades avec tous les champs requis."""
        trades_data = []
        cumulative_r = 0.0
        
        for i, t in enumerate(result.trades):
            # Calculer r_multiple correctement
            # r_multiple = pnl_$ / risk_$ (signé)
            risk_dollars = t.risk_amount or (engine.risk_engine.state.base_r_unit_dollars * 2)
            r_multiple = t.pnl_dollars / risk_dollars if risk_dollars > 0 else 0.0
            
            # pnl_R_account basé sur base_r_unit
            base_r = engine.risk_engine.state.base_r_unit_dollars
            pnl_r_account = t.pnl_dollars / base_r if base_r > 0 else 0.0
            
            cumulative_r += pnl_r_account
            
            trades_data.append({
                "trade_id": t.trade_id,
                "timestamp_entry": t.timestamp_entry,
                "timestamp_exit": t.timestamp_exit,
                "date": t.timestamp_entry.date().isoformat() if t.timestamp_entry else None,
                "month": t.timestamp_entry.strftime("%Y-%m") if t.timestamp_entry else None,
                "symbol": t.symbol,
                "playbook": t.playbook,
                "direction": t.direction,
                "trade_type": t.trade_type,
                "quality": t.quality,
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "stop_loss": t.stop_loss,
                "position_size": t.position_size,
                "pnl_dollars": t.pnl_dollars,
                "risk_dollars": risk_dollars,
                "r_multiple": r_multiple,
                "risk_tier": getattr(t, 'risk_tier', 2),
                "pnl_R_account": pnl_r_account,
                "cumulative_R": cumulative_r,
                "outcome": t.outcome,
                "exit_reason": t.exit_reason,
            })
        
        return trades_data
    
    def run_ablation_all(self) -> Dict[str, Dict[str, Any]]:
        """
        Exécute tous les scénarios d'ablation standard.
        
        Returns:
            Dict avec tous les résultats par scénario
        """
        logger.info("\n" + "="*80)
        logger.info("ABLATION RUNNER - Exécution de tous les scénarios")
        logger.info("="*80)
        
        for scenario_id, config in ABLATION_SCENARIOS.items():
            # Skip DAY_Aplus_1 car désactivé
            if "day_aplus" in scenario_id:
                logger.info(f"\n⏭️ Skipping {scenario_id} (désactivé)")
                continue
            
            try:
                self.run_scenario(
                    scenario_id=scenario_id,
                    playbooks=config["playbooks"],
                    description=config["description"],
                )
            except Exception as e:
                logger.error(f"Erreur sur {scenario_id}: {e}")
                self.results[scenario_id] = {"error": str(e)}
        
        # Générer rapport comparatif
        self._generate_comparison_report()
        
        return self.results
    
    def _generate_comparison_report(self):
        """Génère un rapport comparatif de tous les scénarios."""
        comparison = {
            "generated_at": datetime.now().isoformat(),
            "mode": self.mode,
            "scenarios": {},
        }
        
        for scenario_id, result in self.results.items():
            if "error" in result:
                comparison["scenarios"][scenario_id] = {"error": result["error"]}
            elif "global_metrics" in result:
                m = result["global_metrics"]
                comparison["scenarios"][scenario_id] = {
                    "playbooks": result["playbooks"],
                    "total_r": m["total_r"],
                    "total_trades": m["total_trades"],
                    "total_days": m.get("total_days"),
                    "trades_per_day": m.get("trades_per_day"),
                    "winrate": m["winrate"],
                    "profit_factor": m["profit_factor"],
                    "expectancy_r": m["expectancy_r"],
                    "max_drawdown_r": m["max_drawdown_r"],
                }
        
        comparison_path = self.output_dir / "comparison_report.json"
        with comparison_path.open("w", encoding="utf-8") as f:
            json.dump(comparison, f, indent=2)
        
        logger.info(f"\n📋 Rapport comparatif: {comparison_path}")
        
        # Afficher tableau comparatif
        logger.info("\n" + "="*80)
        logger.info("COMPARAISON DES SCÉNARIOS")
        logger.info("="*80)
        logger.info(f"{'Scénario':<25} {'Trades':>8} {'WR':>8} {'Total R':>10} {'PF':>8} {'MaxDD':>8}")
        logger.info("-"*80)
        
        for scenario_id, data in comparison["scenarios"].items():
            if "error" in data:
                logger.info(f"{scenario_id:<25} {'ERROR':>8}")
            else:
                logger.info(
                    f"{scenario_id:<25} "
                    f"{data['total_trades']:>8} "
                    f"{data['winrate']:>7.1f}% "
                    f"{data['total_r']:>+9.2f}R "
                    f"{data['profit_factor']:>7.2f} "
                    f"{data['max_drawdown_r']:>7.2f}R"
                )


def main():
    parser = argparse.ArgumentParser(description="Ablation Runner pour backtests DexterioBOT")
    parser.add_argument("--mode", default="AGGRESSIVE", help="Trading mode (AGGRESSIVE/SAFE)")
    parser.add_argument("--from", dest="date_from", help="Date de début (YYYY-MM-DD)")
    parser.add_argument("--to", dest="date_to", help="Date de fin (YYYY-MM-DD)")
    parser.add_argument("--playbooks", nargs="+", help="Playbooks à activer")
    parser.add_argument("--ablation-all", action="store_true", help="Lancer tous les scénarios d'ablation")
    parser.add_argument("--symbols", default="SPY,QQQ", help="Symboles séparés par virgule (ex: SPY,QQQ)")
    parser.add_argument("--data-dir", default=str(historical_data_path('1m')), help="Répertoire des Parquet 1m")
    parser.add_argument("--output-dir", default=str(backtest_results_path('ablation')), help="Répertoire de sortie")
    
    args = parser.parse_args()

    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    
    runner = AblationRunner(
        mode=args.mode,
        symbols=symbols,
        output_dir=args.output_dir,
        data_dir=args.data_dir,
    )
    
    if args.ablation_all:
        runner.run_ablation_all()
    elif args.playbooks:
        scenario_id = "_".join(p.lower().replace("_", "")[:10] for p in args.playbooks)
        runner.run_scenario(
            scenario_id=scenario_id,
            playbooks=args.playbooks,
            date_from=args.date_from,
            date_to=args.date_to,
            description=f"Custom: {', '.join(args.playbooks)}",
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
