"""
Script: lance un backtest direct (sans API) et vérifie les artefacts.
Usage: depuis backend/ : python scripts/run_backtest_verify.py
"""
import sys
import json
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from models.backtest import BacktestConfig
from backtest.engine import BacktestEngine
from utils.path_resolver import historical_data_path, results_path

def main():
    run_id = "verify_sprint3"
    run_name = f"job_{run_id}"
    symbols = ["SPY"]
    data_paths = []
    for sym in symbols:
        p = historical_data_path("1m", f"{sym}.parquet")
        if not p.exists():
            print(f"SKIP: Data not found {p}")
            return 1
        data_paths.append(str(p))

    config = BacktestConfig(
        run_name=run_name,
        symbols=symbols,
        data_paths=data_paths,
        start_date="2025-08-04",
        end_date="2025-08-05",
        trading_mode="AGGRESSIVE",
        trade_types=["DAILY", "SCALP"],
        htf_warmup_days=40,
        initial_capital=50000.0,
        commission_model="ibkr_fixed",
        enable_reg_fees=True,
        slippage_model="pct",
        slippage_cost_pct=0.0005,
        spread_model="fixed_bps",
        spread_bps=2.0,
        output_dir=str(results_path()),
    )

    print("Running backtest...")
    engine = BacktestEngine(config)
    engine.load_data()
    result = engine.run()
    print(f"Backtest done: {result.total_trades} trades")

    output_dir = Path(config.output_dir)
    mode = config.trading_mode
    types = "_".join(config.trade_types)

    # Vérifications
    verification_path = output_dir / f"post_run_verification_{run_name}.json"
    trades_csv = output_dir / f"trades_{run_name}_{mode}_{types}.csv"
    grading_debug = output_dir / f"grading_debug_{run_name}.json"
    mc_debug = output_dir / f"master_candle_debug_{run_name}.json"

    print("\n--- VERIFICATION ---")
    print(f"post_run_verification exists: {verification_path.exists()} -> {verification_path}")
    print(f"trades_csv exists: {trades_csv.exists()} -> {trades_csv}")
    print(f"grading_debug exists: {grading_debug.exists()} -> {grading_debug}")
    print(f"master_candle_debug exists: {mc_debug.exists()} -> {mc_debug}")

    if verification_path.exists():
        with open(verification_path, "r", encoding="utf-8") as f:
            v = json.load(f)
        print(f"\npost_run_verification.pass: {v.get('pass')}")
        print(f"failures: {v.get('failures', [])}")
        if v.get("grading_validation"):
            print(f"grading_validation.pass: {v['grading_validation'].get('pass')}")
        if v.get("master_candle_validation"):
            print(f"master_candle_validation.pass: {v['master_candle_validation'].get('pass')}")
        if v.get("lookahead_detector"):
            print(f"lookahead_detector.pass: {v['lookahead_detector'].get('pass')}")
        return 0 if v.get("pass") else 1
    print("FAIL: post_run_verification not found")
    return 1

if __name__ == "__main__":
    sys.exit(main())
