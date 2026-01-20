#!/usr/bin/env python3
"""
P2-2.B B3 Debug - HTF Warmup Execution Trace

Instruments backtest to prove exactly where warmup breaks.
"""
import sys
import json
import logging
from pathlib import Path
import pandas as pd

# Configure logging BEFORE imports
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s',
    force=True
)

_backend_dir = Path(__file__).parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from models.backtest import BacktestConfig
from backtest.engine import BacktestEngine
from utils.path_resolver import historical_data_path, results_path


def debug_htf_warmup():
    """Run instrumented backtest with debug checkpoints."""
    
    print("="*80)
    print("HTF WARMUP DEBUG - EXECUTION TRACE")
    print("="*80)
    print()
    
    # Config with warmup - Use date with sufficient history
    config = BacktestConfig(
        run_name="htf_warmup_debug",
        symbols=["SPY"],  # Single symbol for simplicity
        data_paths=[str(historical_data_path("1m", "SPY.parquet"))],
        start_date="2025-08-01",  # 40+ days after data start
        end_date="2025-08-01",
        trading_mode="AGGRESSIVE",
        trade_types=["DAILY"],
        htf_warmup_days=40,  # 40 days to ensure >= 20 trading days
        export_market_state=True
    )
    
    print(f"Config:")
    print(f"  start_date: {config.start_date}")
    print(f"  end_date: {config.end_date}")
    print(f"  htf_warmup_days: {config.htf_warmup_days}")
    print()
    
    # Create debug trace
    debug_trace = {
        "config": {
            "start_date": config.start_date,
            "end_date": config.end_date,
            "htf_warmup_days": config.htf_warmup_days,
            "warmup_start_date": None,
        },
        "checkpoints": {}
    }
    
    # Calculate expected warmup start
    if config.start_date and config.htf_warmup_days > 0:
        warmup_start = pd.to_datetime(config.start_date) - pd.Timedelta(days=config.htf_warmup_days)
        debug_trace["config"]["warmup_start_date"] = warmup_start.strftime('%Y-%m-%d')
    
    # Create engine
    engine = BacktestEngine(config)
    
    # Checkpoint 1: After load_data()
    print("📍 Checkpoint 1: load_data()")
    engine.load_data()
    
    # Check htf_warmup_data
    warmup_loaded = hasattr(engine, 'htf_warmup_data') and bool(engine.htf_warmup_data)
    debug_trace["checkpoints"]["1_after_load_data"] = {
        "htf_warmup_data_exists": warmup_loaded,
        "htf_warmup_data_keys": list(engine.htf_warmup_data.keys()) if warmup_loaded else [],
        "htf_warmup_rows": {
            sym: len(df) for sym, df in engine.htf_warmup_data.items()
        } if warmup_loaded else {},
        "combined_data_rows": len(engine.combined_data) if engine.combined_data is not None else 0,
    }
    
    print(f"  warmup_loaded: {warmup_loaded}")
    if warmup_loaded:
        for sym, df in engine.htf_warmup_data.items():
            print(f"  {sym}: {len(df)} warmup bars")
    
    # Checkpoint 2: Aggregator state before run
    print("\n📍 Checkpoint 2: Before run() - Aggregator state")
    
    # Check aggregator exists and has warmup data
    agg_exists = hasattr(engine, 'tf_aggregator')
    if agg_exists:
        candles_1d_before = engine.tf_aggregator.get_candles("SPY", "1d")
        candles_4h_before = engine.tf_aggregator.get_candles("SPY", "4h")
        
        debug_trace["checkpoints"]["2_before_run"] = {
            "aggregator_exists": True,
            "candles_1d_count": len(candles_1d_before),
            "candles_4h_count": len(candles_4h_before),
        }
        
        print(f"  candles_1d: {len(candles_1d_before)}")
        print(f"  candles_4h: {len(candles_4h_before)}")
    else:
        debug_trace["checkpoints"]["2_before_run"] = {
            "aggregator_exists": False
        }
        print(f"  ❌ Aggregator not found!")
    
    # Run backtest
    print("\n📍 Running backtest...")
    result = engine.run()
    
    print(f"  Bars: {result.total_bars}")
    print(f"  Setups: {len(engine.all_generated_setups)}")
    print(f"  Trades: {result.total_trades}")
    
    # Checkpoint 3: After run - Aggregator state
    print("\n📍 Checkpoint 3: After run() - Aggregator state")
    
    candles_1d_after = engine.tf_aggregator.get_candles("SPY", "1d")
    candles_4h_after = engine.tf_aggregator.get_candles("SPY", "4h")
    
    debug_trace["checkpoints"]["3_after_run"] = {
        "candles_1d_count": len(candles_1d_after),
        "candles_4h_count": len(candles_4h_after),
    }
    
    print(f"  candles_1d: {len(candles_1d_after)}")
    print(f"  candles_4h: {len(candles_4h_after)}")
    
    # Checkpoint 4: Market state analysis
    print("\n📍 Checkpoint 4: Market state")
    
    if engine.market_state_records:
        df = pd.DataFrame(engine.market_state_records)
        
        from collections import Counter
        day_type_counts = Counter(df['day_type'])
        struct_counts = Counter(df['daily_structure'])
        
        debug_trace["checkpoints"]["4_market_state"] = {
            "total_records": len(df),
            "day_type_distribution": dict(day_type_counts),
            "daily_structure_distribution": dict(struct_counts),
            "day_type_unknown_pct": round(day_type_counts.get('unknown', 0) / len(df) * 100, 1),
            "daily_structure_unknown_pct": round(struct_counts.get('unknown', 0) / len(df) * 100, 1),
        }
        
        print(f"  day_type unknown: {day_type_counts.get('unknown', 0)}/{len(df)} ({debug_trace['checkpoints']['4_market_state']['day_type_unknown_pct']}%)")
        print(f"  daily_structure unknown: {struct_counts.get('unknown', 0)}/{len(df)} ({debug_trace['checkpoints']['4_market_state']['daily_structure_unknown_pct']}%)")
    
    # Checkpoint 5: Prefeed gate inspection
    print("\n📍 Checkpoint 5: Prefeed gate (from engine)")
    
    if hasattr(engine, '_debug_checkpoints'):
        for checkpoint_name, checkpoint_data in engine._debug_checkpoints:
            if checkpoint_name == "prefeed_gate":
                debug_trace["checkpoints"]["5_prefeed_gate"] = checkpoint_data
                
                print(f"  hasattr_htf_warmup_data: {checkpoint_data.get('hasattr_htf_warmup_data')}")
                print(f"  bool_htf_warmup_data: {checkpoint_data.get('bool_htf_warmup_data')}")
                print(f"  len_htf_warmup_data: {checkpoint_data.get('len_htf_warmup_data')}")
                print(f"  id: {checkpoint_data.get('id_htf_warmup_data')}")
                break
    else:
        print("  ❌ No _debug_checkpoints found")
    
    # Save debug trace
    output_path = results_path("htf_warmup_debug_2025-08-01_after.json")
    with open(output_path, 'w') as f:
        json.dump(debug_trace, f, indent=2)
    
    print(f"\n✅ Debug trace saved: {output_path}")
    
    # Analysis
    print(f"\n{'='*80}")
    print("ANALYSIS")
    print(f"{'='*80}\n")
    
    # Check 1: Branch taken?
    if warmup_loaded:
        print("✅ Warmup branch TAKEN")
        warmup_rows = sum(debug_trace["checkpoints"]["1_after_load_data"]["htf_warmup_rows"].values())
        print(f"   {warmup_rows} warmup rows loaded")
    else:
        print("❌ Warmup branch NOT TAKEN")
        print("   Check: start_date and htf_warmup_days in config")
    
    # Check 2: Prefeed worked?
    candles_before = debug_trace["checkpoints"]["2_before_run"]["candles_1d_count"]
    if candles_before >= 20:
        print(f"✅ Prefeed WORKED: {candles_before} daily candles before run")
    elif candles_before > 0:
        print(f"⚠️  Prefeed PARTIAL: {candles_before} daily candles (need 20)")
    else:
        print(f"❌ Prefeed FAILED: {candles_before} daily candles before run")
    
    # Check 3: Reset after prefeed?
    candles_after = debug_trace["checkpoints"]["3_after_run"]["candles_1d_count"]
    if candles_before > 0 and candles_after < candles_before:
        print(f"🔴 RESET DETECTED: {candles_before} → {candles_after} daily candles")
        print(f"   Aggregator was replaced/reset during run()")
    elif candles_after >= candles_before:
        print(f"✅ No reset: {candles_before} → {candles_after} daily candles")
    
    # Check 4: Result
    unknown_pct = debug_trace["checkpoints"]["4_market_state"]["day_type_unknown_pct"]
    if unknown_pct < 100:
        print(f"✅ SUCCESS: day_type unknown {unknown_pct}% (< 100%)")
    else:
        print(f"❌ FAILED: day_type unknown {unknown_pct}% (still 100%)")
    
    print(f"\n{'='*80}")
    
    return debug_trace


if __name__ == "__main__":
    debug_htf_warmup()
