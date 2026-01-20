#!/usr/bin/env python3
"""
P2-2.A - Baselines R Generator

Génère 3 baselines R propres pour mesure de performance système actuel.
Utilise UNIQUEMENT metrics.py (formules verrouillées).

Baselines:
1. 1 jour (2025-06-03)
2. 5 jours (2025-06-03 → 2025-06-09)
3. 1 mois (juin 2025)

Métriques:
- total_R, expectancy_R, profit_factor, maxDD_R
- trades_count, wins, losses, winrate
- R_distribution, R_per_playbook
"""
import sys
import json
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np

_backend_dir = Path(__file__).parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from models.backtest import BacktestConfig
from backtest.engine import BacktestEngine
from backtest.metrics import calculate_metrics, calculate_playbook_metrics
from utils.path_resolver import historical_data_path, results_path


def generate_baseline_r(
    name: str,
    start_date: str = None,
    end_date: str = None,
    symbols: list = None
) -> dict:
    """
    Génère une baseline R pour une période.
    
    Args:
        name: "1d", "5d", ou "month"
        start_date: YYYY-MM-DD (None = all data)
        end_date: YYYY-MM-DD (None = all data)
        symbols: Liste symboles (default: ["SPY", "QQQ"])
    
    Returns:
        Dict avec toutes métriques R
    """
    symbols = symbols or ["SPY", "QQQ"]
    
    print(f"\n{'='*80}")
    print(f"📊 Generating Baseline R: {name}")
    print(f"{'='*80}")
    if start_date:
        print(f"Period: {start_date} → {end_date}")
    else:
        print(f"Period: Full dataset")
    print(f"Symbols: {', '.join(symbols)}")
    
    # Config backtest
    config = BacktestConfig(
        run_name=f"baseline_r_{name}",
        symbols=symbols,
        data_paths=[str(historical_data_path("1m", f"{sym}.parquet")) for sym in symbols],
        start_date=start_date,
        end_date=end_date,
        initial_capital=50000.0,
        trading_mode="AGGRESSIVE",
        trade_types=["DAILY", "SCALP"]
    )
    
    # Run backtest
    engine = BacktestEngine(config)
    engine.load_data()
    
    print(f"Loaded: {len(engine.combined_data)} bars")
    
    result = engine.run()
    
    print(f"Processed: {result.total_bars} bars")
    print(f"Trades: {result.total_trades}")
    
    # Préparer données trades pour metrics.py
    trades_data = []
    for trade in engine.trades:
        trades_data.append({
            "trade_id": trade.trade_id,
            "symbol": trade.symbol,
            "playbook": trade.playbook,
            "direction": trade.direction,
            "trade_type": trade.trade_type,
            "quality": trade.quality,
            "entry_price": trade.entry_price,
            "exit_price": trade.exit_price,
            "stop_loss": trade.stop_loss,
            "pnl_dollars": trade.pnl_dollars,
            "risk_dollars": trade.risk_amount,  # risk_amount not risk_dollars
            "r_multiple": trade.pnl_r,  # pnl_r not r_multiple
            "pnl_R_account": trade.pnl_r,  # Use same as r_multiple for now
            "outcome": trade.outcome,
            "exit_reason": trade.exit_reason,
            "date": trade.timestamp_entry.strftime('%Y-%m-%d') if trade.timestamp_entry else None,
            "month": trade.timestamp_entry.strftime('%Y-%m') if trade.timestamp_entry else None,
        })
    
    # Calculer métriques via metrics.py (formules verrouillées)
    metrics = calculate_metrics(trades_data) if trades_data else {}
    
    # Métriques par playbook
    playbook_metrics = calculate_playbook_metrics(trades_data) if trades_data else {}
    
    # Distribution R
    r_multiples = [t["r_multiple"] for t in trades_data]
    r_distribution = {
        "min": float(np.min(r_multiples)) if r_multiples else 0.0,
        "max": float(np.max(r_multiples)) if r_multiples else 0.0,
        "mean": float(np.mean(r_multiples)) if r_multiples else 0.0,
        "median": float(np.median(r_multiples)) if r_multiples else 0.0,
        "std": float(np.std(r_multiples)) if r_multiples else 0.0,
        "quartiles": {
            "Q1": float(np.percentile(r_multiples, 25)) if r_multiples else 0.0,
            "Q2": float(np.percentile(r_multiples, 50)) if r_multiples else 0.0,
            "Q3": float(np.percentile(r_multiples, 75)) if r_multiples else 0.0,
        },
        "histogram": {
            "bins": ["<-2R", "-2R to -1R", "-1R to 0R", "0R to 1R", "1R to 2R", "2R to 3R", ">3R"],
            "counts": [
                sum(1 for r in r_multiples if r < -2),
                sum(1 for r in r_multiples if -2 <= r < -1),
                sum(1 for r in r_multiples if -1 <= r < 0),
                sum(1 for r in r_multiples if 0 <= r < 1),
                sum(1 for r in r_multiples if 1 <= r < 2),
                sum(1 for r in r_multiples if 2 <= r < 3),
                sum(1 for r in r_multiples if r >= 3),
            ]
        }
    }
    
    # Construire baseline dict
    baseline = {
        "name": name,
        "timestamp": datetime.utcnow().isoformat(),
        "config": {
            "start_date": start_date,
            "end_date": end_date,
            "symbols": symbols,
            "mode": "AGGRESSIVE",
            "trade_types": ["DAILY", "SCALP"],
            "initial_capital": 50000.0
        },
        "data": {
            "bars_processed": result.total_bars,
            "date_range": f"{result.start_date} → {result.end_date}",
        },
        "metrics_r": {
            "total_R": metrics.get("total_r", 0.0),
            "expectancy_R": metrics.get("expectancy_r", 0.0),
            "profit_factor": metrics.get("profit_factor", 0.0),
            "max_drawdown_R": metrics.get("max_drawdown_r", 0.0),
            "trades_count": metrics.get("total_trades", 0),
            "wins": metrics.get("wins", 0),
            "losses": metrics.get("losses", 0),
            "breakevens": metrics.get("breakevens", 0),
            "winrate": metrics.get("winrate", 0.0),
            "avg_win_R": metrics.get("avg_win_r", 0.0),
            "avg_loss_R": metrics.get("avg_loss_r", 0.0),
            "max_consecutive_losses": metrics.get("max_consecutive_losses", 0),
            "trades_per_day": metrics.get("trades_per_day", 0.0),
        },
        "r_distribution": r_distribution,
        "r_per_playbook": {
            playbook: {
                "total_trades": pb_metrics.get("total_trades", 0),
                "total_R": pb_metrics.get("total_r", 0.0),
                "expectancy_R": pb_metrics.get("expectancy_r", 0.0),
                "winrate": pb_metrics.get("winrate", 0.0)
            }
            for playbook, pb_metrics in playbook_metrics.items()
        },
        "trades": trades_data,
        "equity_curve_R": engine.equity_curve_r,
        "equity_timestamps": [ts.isoformat() for ts in engine.equity_timestamps]
    }
    
    # Afficher résumé
    print(f"\n📈 Results:")
    print(f"  Total R: {baseline['metrics_r']['total_R']:.3f}")
    print(f"  Expectancy R: {baseline['metrics_r']['expectancy_R']:.3f}")
    print(f"  Profit Factor: {baseline['metrics_r']['profit_factor']:.2f}")
    print(f"  Max DD R: {baseline['metrics_r']['max_drawdown_R']:.3f}")
    print(f"  Trades: {baseline['metrics_r']['trades_count']} (W:{baseline['metrics_r']['wins']}, L:{baseline['metrics_r']['losses']})")
    print(f"  Winrate: {baseline['metrics_r']['winrate']:.1f}%")
    
    return baseline


def save_baseline(baseline: dict):
    """Sauvegarde baseline avec artefacts."""
    
    name = baseline["name"]
    
    # JSON metrics
    metrics_path = results_path(f"metrics_baseline_{name}.json")
    with open(metrics_path, 'w') as f:
        # Exclude trades list and equity curve from JSON (too large)
        baseline_json = baseline.copy()
        trades = baseline_json.pop("trades")
        equity_curve = baseline_json.pop("equity_curve_R")
        equity_ts = baseline_json.pop("equity_timestamps")
        
        json.dump(baseline_json, f, indent=2)
    
    print(f"✅ Saved: {metrics_path}")
    
    # Trades parquet
    if baseline["trades"]:
        trades_df = pd.DataFrame(baseline["trades"])
        trades_path = results_path(f"trades_baseline_{name}.parquet")
        trades_df.to_parquet(trades_path, index=False)
        print(f"✅ Saved: {trades_path}")
    
    # Equity curve parquet
    if baseline["equity_curve_R"]:
        equity_df = pd.DataFrame({
            "timestamp": pd.to_datetime(baseline["equity_timestamps"]),
            "equity_R": baseline["equity_curve_R"]
        })
        equity_path = results_path(f"equity_curve_{name}.parquet")
        equity_df.to_parquet(equity_path, index=False)
        print(f"✅ Saved: {equity_path}")


def main():
    """Génère les 3 baselines R."""
    
    print("=" * 80)
    print("P2-2.A - BASELINES R GENERATION")
    print("=" * 80)
    print("\nObjectif: Mesurer performance système actuel (AGGRESSIVE mode)")
    print("Métriques: formules verrouillées (metrics.py)")
    print()
    
    # Baseline 1: 1 jour
    baseline_1d = generate_baseline_r(
        name="1d",
        start_date="2025-06-03",
        end_date="2025-06-03",
        symbols=["SPY", "QQQ"]
    )
    save_baseline(baseline_1d)
    
    # Baseline 2: 5 jours
    baseline_5d = generate_baseline_r(
        name="5d",
        start_date="2025-06-03",
        end_date="2025-06-09",
        symbols=["SPY", "QQQ"]
    )
    save_baseline(baseline_5d)
    
    # Baseline 3: 1 mois (juin 2025)
    baseline_month = generate_baseline_r(
        name="month",
        start_date="2025-06-01",
        end_date="2025-06-30",
        symbols=["SPY", "QQQ"]
    )
    save_baseline(baseline_month)
    
    # Résumé final
    print("\n" + "=" * 80)
    print("✅ BASELINES R GENERATION COMPLETE")
    print("=" * 80)
    
    print("\n📊 Summary:")
    print(f"\n1-Day Baseline:")
    print(f"  Total R: {baseline_1d['metrics_r']['total_R']:.3f}")
    print(f"  Trades: {baseline_1d['metrics_r']['trades_count']}")
    print(f"  PF: {baseline_1d['metrics_r']['profit_factor']:.2f}")
    
    print(f"\n5-Day Baseline:")
    print(f"  Total R: {baseline_5d['metrics_r']['total_R']:.3f}")
    print(f"  Trades: {baseline_5d['metrics_r']['trades_count']}")
    print(f"  PF: {baseline_5d['metrics_r']['profit_factor']:.2f}")
    
    print(f"\nMonth Baseline (June 2025):")
    print(f"  Total R: {baseline_month['metrics_r']['total_R']:.3f}")
    print(f"  Trades: {baseline_month['metrics_r']['trades_count']}")
    print(f"  PF: {baseline_month['metrics_r']['profit_factor']:.2f}")
    
    print("\n📁 Artifacts:")
    print(f"  backend/results/metrics_baseline_1d.json")
    print(f"  backend/results/metrics_baseline_5d.json")
    print(f"  backend/results/metrics_baseline_month.json")
    print(f"  backend/results/equity_curve_*.parquet")
    print(f"  backend/results/trades_baseline_*.parquet")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
