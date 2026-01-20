#!/usr/bin/env python3
"""
Date Slicing Proof Generator

Runs date slicing tests and generates JSON proof artifact.
"""
import sys
import json
from pathlib import Path

_backend_dir = Path(__file__).parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from models.backtest import BacktestConfig
from backtest.engine import BacktestEngine
from utils.path_resolver import historical_data_path, results_path
import pandas as pd


def generate_proof():
    """Generate date slicing proof."""
    
    symbol = "SPY"
    
    # Full dataset
    config_full = BacktestConfig(
        run_name="proof_full",
        symbols=[symbol],
        data_paths=[str(historical_data_path("1m", f"{symbol}.parquet"))],
        trading_mode="AGGRESSIVE"
    )
    
    engine_full = BacktestEngine(config_full)
    engine_full.load_data()
    
    bars_full = len(engine_full.combined_data)
    date_min_full = engine_full.combined_data['datetime'].min()
    date_max_full = engine_full.combined_data['datetime'].max()
    
    # 1 day slice
    config_1d = BacktestConfig(
        run_name="proof_1d",
        symbols=[symbol],
        data_paths=[str(historical_data_path("1m", f"{symbol}.parquet"))],
        trading_mode="AGGRESSIVE",
        start_date="2025-06-03",
        end_date="2025-06-03"
    )
    
    engine_1d = BacktestEngine(config_1d)
    engine_1d.load_data()
    
    bars_1d = len(engine_1d.combined_data)
    date_min_1d = engine_1d.combined_data['datetime'].min()
    date_max_1d = engine_1d.combined_data['datetime'].max()
    
    # 5 days slice
    config_5d = BacktestConfig(
        run_name="proof_5d",
        symbols=[symbol],
        data_paths=[str(historical_data_path("1m", f"{symbol}.parquet"))],
        trading_mode="AGGRESSIVE",
        start_date="2025-06-03",
        end_date="2025-06-09"
    )
    
    engine_5d = BacktestEngine(config_5d)
    engine_5d.load_data()
    
    bars_5d = len(engine_5d.combined_data)
    date_min_5d = engine_5d.combined_data['datetime'].min()
    date_max_5d = engine_5d.combined_data['datetime'].max()
    
    # Build proof
    proof = {
        "test": "date_slicing",
        "symbol": symbol,
        "timeframe": "1m",
        "full_dataset": {
            "bars": bars_full,
            "date_min": str(date_min_full),
            "date_max": str(date_max_full),
            "config": {
                "start_date": None,
                "end_date": None
            }
        },
        "slice_1d": {
            "bars": bars_1d,
            "date_min": str(date_min_1d),
            "date_max": str(date_max_1d),
            "config": {
                "start_date": "2025-06-03",
                "end_date": "2025-06-03"
            },
            "reduction_factor": round(bars_full / bars_1d, 1),
            "percentage_of_full": round(bars_1d / bars_full * 100, 2)
        },
        "slice_5d": {
            "bars": bars_5d,
            "date_min": str(date_min_5d),
            "date_max": str(date_max_5d),
            "config": {
                "start_date": "2025-06-03",
                "end_date": "2025-06-09"
            },
            "reduction_factor": round(bars_full / bars_5d, 1),
            "percentage_of_full": round(bars_5d / bars_full * 100, 2)
        },
        "assertions": {
            "1d_less_than_full": bars_1d < bars_full,
            "5d_less_than_full": bars_5d < bars_full,
            "5d_greater_than_1d": bars_5d > bars_1d,
            "1d_within_range": 600 <= bars_1d <= 1000,
            "5d_within_range": 3000 <= bars_5d <= 5000,
            "ratio_5d_1d": round(bars_5d / bars_1d, 2),
            "ratio_reasonable": 3 < (bars_5d / bars_1d) < 7
        },
        "verdict": "PASS" if all([
            bars_1d < bars_full,
            bars_5d < bars_full,
            bars_5d > bars_1d,
            600 <= bars_1d <= 1000,
            3000 <= bars_5d <= 5000,
            3 < (bars_5d / bars_1d) < 7
        ]) else "FAIL"
    }
    
    # Save
    output_path = results_path("date_slicing_proof.json")
    with open(output_path, 'w') as f:
        json.dump(proof, f, indent=2)
    
    print(f"✅ Date slicing proof generated: {output_path}")
    print(f"   Full: {bars_full} bars")
    print(f"   1d:   {bars_1d} bars ({proof['slice_1d']['reduction_factor']}x faster)")
    print(f"   5d:   {bars_5d} bars ({proof['slice_5d']['reduction_factor']}x faster)")
    print(f"   Verdict: {proof['verdict']}")
    
    return proof['verdict'] == "PASS"


if __name__ == "__main__":
    success = generate_proof()
    sys.exit(0 if success else 1)
