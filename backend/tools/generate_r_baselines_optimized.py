#!/usr/bin/env python3
"""
P2-2.A - Baselines R Generator (OPTIMISÉ)

Génère baselines 1d + 5d en direct.
Utilise rolling_2025-06 existant pour month.

Stratégie pragmatique:
- 1d/5d: date slicing (rapide)
- Month: run existant (déjà validé)
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


def generate_baseline_micro(
    name: str,
    start_date: str,
    end_date: str,
    symbols: list = ["SPY", "QQQ"]
) -> dict:
    """Génère baseline micro (1d ou 5d)."""
    
    print(f"\n{'='*80}")
    print(f"📊 Generating Baseline R: {name}")
    print(f"{'='*80}")
    print(f"Period: {start_date} → {end_date}")
    print(f"Symbols: {', '.join(symbols)}")
    
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
    
    engine = BacktestEngine(config)
    engine.load_data()
    result = engine.run()
    
    print(f"Bars: {result.total_bars} | Trades: {result.total_trades}")
    
    # Trades data
    trades_data = []
    for trade in engine.trades:
        trades_data.append({
            "trade_id": trade.trade_id,
            "symbol": trade.symbol,
            "playbook": trade.playbook,
            "r_multiple": trade.pnl_r,
            "pnl_R_account": trade.pnl_r,
            "outcome": trade.outcome,
            "date": trade.timestamp_entry.strftime('%Y-%m-%d') if trade.timestamp_entry else None,
        })
    
    # Metrics via metrics.py
    metrics = calculate_metrics(trades_data) if trades_data else {}
    playbook_metrics = calculate_playbook_metrics(trades_data) if trades_data else {}
    
    # R distribution
    r_multiples = [t["r_multiple"] for t in trades_data]
    
    baseline = {
        "name": name,
        "period": f"{start_date} → {end_date}",
        "bars": result.total_bars,
        "metrics_r": {
            "total_R": metrics.get("total_r", 0.0),
            "expectancy_R": metrics.get("expectancy_r", 0.0),
            "profit_factor": metrics.get("profit_factor", 0.0),
            "max_drawdown_R": metrics.get("max_drawdown_r", 0.0),
            "trades_count": metrics.get("total_trades", 0),
            "wins": metrics.get("wins", 0),
            "losses": metrics.get("losses", 0),
            "winrate": metrics.get("winrate", 0.0),
        },
        "r_distribution": {
            "r_multiples": r_multiples,
            "mean": float(np.mean(r_multiples)) if r_multiples else 0.0,
            "median": float(np.median(r_multiples)) if r_multiples else 0.0,
            "trades_above_1r": sum(1 for r in r_multiples if r > 1.0),
            "trades_above_2r": sum(1 for r in r_multiples if r > 2.0),
        },
        "r_by_playbook": {
            pb: {
                "trades": m.get("total_trades", 0),
                "total_R": m.get("total_r", 0.0),
                "expectancy_R": m.get("expectancy_r", 0.0),
            }
            for pb, m in playbook_metrics.items()
        },
        "equity_curve_R": engine.equity_curve_r,
        "equity_timestamps": [ts.isoformat() for ts in engine.equity_timestamps],
    }
    
    print(f"✅ Total R: {baseline['metrics_r']['total_R']:.3f} | PF: {baseline['metrics_r']['profit_factor']:.2f}")
    
    return baseline


def consolidate_month_from_existing() -> dict:
    """Consolide month baseline depuis rolling_2025-06."""
    
    print(f"\n{'='*80}")
    print(f"📊 Consolidating Month Baseline from rolling_2025-06")
    print(f"{'='*80}")
    
    # Load existing trades
    trades_df = pd.read_parquet(results_path("baseline_trades_reference.parquet"))
    
    trades_data = []
    for _, row in trades_df.iterrows():
        trades_data.append({
            "r_multiple": row["r_multiple"],
            "pnl_R_account": row["pnl_R_account"],
            "outcome": row["outcome"],
            "playbook": row["playbook"],
            "date": row["date"],
        })
    
    # Metrics
    metrics = calculate_metrics(trades_data)
    playbook_metrics = calculate_playbook_metrics(trades_data)
    
    # R distribution
    r_multiples = [t["r_multiple"] for t in trades_data]
    
    # Equity curve
    equity_df = pd.read_parquet(results_path("baseline_equity_reference.parquet"))
    
    baseline = {
        "name": "month",
        "period": "2025-06-01 → 2025-06-30",
        "source": "rolling_2025-06 (existing run)",
        "bars": "~216,574 (SPY+QQQ combined)",
        "metrics_r": {
            "total_R": metrics.get("total_r", 0.0),
            "expectancy_R": metrics.get("expectancy_r", 0.0),
            "profit_factor": metrics.get("profit_factor", 0.0),
            "max_drawdown_R": metrics.get("max_drawdown_r", 0.0),
            "trades_count": metrics.get("total_trades", 0),
            "wins": metrics.get("wins", 0),
            "losses": metrics.get("losses", 0),
            "winrate": metrics.get("winrate", 0.0),
        },
        "r_distribution": {
            "r_multiples": r_multiples,
            "mean": float(np.mean(r_multiples)) if r_multiples else 0.0,
            "median": float(np.median(r_multiples)) if r_multiples else 0.0,
            "trades_above_1r": sum(1 for r in r_multiples if r > 1.0),
            "trades_above_2r": sum(1 for r in r_multiples if r > 2.0),
        },
        "r_by_playbook": {
            pb: {
                "trades": m.get("total_trades", 0),
                "total_R": m.get("total_r", 0.0),
                "expectancy_R": m.get("expectancy_r", 0.0),
            }
            for pb, m in playbook_metrics.items()
        },
        "equity_curve_R": equity_df["equity_R"].tolist() if "equity_R" in equity_df.columns else [],
        "equity_timestamps": equity_df["timestamp"].dt.strftime('%Y-%m-%dT%H:%M:%S').tolist() if "timestamp" in equity_df.columns else [],
    }
    
    print(f"✅ Total R: {baseline['metrics_r']['total_R']:.3f} | Trades: {baseline['metrics_r']['trades_count']}")
    
    return baseline


def save_baseline(baseline: dict):
    """Save baseline artifacts."""
    
    name = baseline["name"]
    
    # Metrics JSON
    metrics_json = {k: v for k, v in baseline.items() if k not in ["equity_curve_R", "equity_timestamps"]}
    metrics_path = results_path(f"metrics_baseline_{name}.json")
    with open(metrics_path, 'w') as f:
        json.dump(metrics_json, f, indent=2)
    print(f"✅ Saved: {metrics_path}")
    
    # R distribution JSON
    r_dist_path = results_path(f"r_distribution_{name}.json")
    with open(r_dist_path, 'w') as f:
        json.dump(baseline["r_distribution"], f, indent=2)
    print(f"✅ Saved: {r_dist_path}")
    
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
    """Generate all baselines."""
    
    print("=" * 80)
    print("P2-2.A - BASELINES R (OPTIMIZED)")
    print("=" * 80)
    print("\nStrategy:")
    print("  - 1d/5d: Direct generation (date slicing)")
    print("  - Month: Consolidate from rolling_2025-06")
    print()
    
    # 1d
    baseline_1d = generate_baseline_micro(
        name="1d",
        start_date="2025-06-03",
        end_date="2025-06-03"
    )
    save_baseline(baseline_1d)
    
    # 5d
    baseline_5d = generate_baseline_micro(
        name="5d",
        start_date="2025-06-03",
        end_date="2025-06-09"
    )
    save_baseline(baseline_5d)
    
    # Month
    baseline_month = consolidate_month_from_existing()
    save_baseline(baseline_month)
    
    # R by playbook (month only, most relevant)
    r_by_playbook_path = results_path("r_by_playbook_month.json")
    with open(r_by_playbook_path, 'w') as f:
        json.dump(baseline_month["r_by_playbook"], f, indent=2)
    print(f"✅ Saved: {r_by_playbook_path}")
    
    # Summary
    print("\n" + "=" * 80)
    print("✅ P2-2.A BASELINES R COMPLETE")
    print("=" * 80)
    
    print("\n📊 Comparison:")
    print(f"\n1-Day:")
    print(f"  Total R: {baseline_1d['metrics_r']['total_R']:.3f}")
    print(f"  Trades: {baseline_1d['metrics_r']['trades_count']}")
    print(f"  Expectancy: {baseline_1d['metrics_r']['expectancy_R']:.3f}R")
    
    print(f"\n5-Day:")
    print(f"  Total R: {baseline_5d['metrics_r']['total_R']:.3f}")
    print(f"  Trades: {baseline_5d['metrics_r']['trades_count']}")
    print(f"  Expectancy: {baseline_5d['metrics_r']['expectancy_R']:.3f}R")
    
    print(f"\nMonth (June 2025):")
    print(f"  Total R: {baseline_month['metrics_r']['total_R']:.3f}")
    print(f"  Trades: {baseline_month['metrics_r']['trades_count']}")
    print(f"  Expectancy: {baseline_month['metrics_r']['expectancy_R']:.3f}R")
    print(f"  PF: {baseline_month['metrics_r']['profit_factor']:.2f}")
    
    print("\n📁 Artifacts:")
    for period in ["1d", "5d", "month"]:
        print(f"  - metrics_baseline_{period}.json")
        print(f"  - r_distribution_{period}.json")
        print(f"  - equity_curve_{period}.parquet")


if __name__ == "__main__":
    main()
