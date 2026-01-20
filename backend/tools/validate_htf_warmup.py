#!/usr/bin/env python3
"""
P2-2.B B3 - HTF Warmup Validation (Before/After)

Compare day_type distribution with and without HTF warmup.
"""
import sys
import json
from pathlib import Path
import pandas as pd
from collections import Counter

_backend_dir = Path(__file__).parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from models.backtest import BacktestConfig
from backtest.engine import BacktestEngine
from utils.path_resolver import historical_data_path, results_path


def run_audit(warmup_days: int, label: str):
    """Run backtest with specified warmup."""
    
    print(f"\n{'='*80}")
    print(f"Running: {label} (warmup={warmup_days} days)")
    print(f"{'='*80}\n")
    
    config = BacktestConfig(
        run_name=f"warmup_test_{label}",
        symbols=["SPY", "QQQ"],
        data_paths=[str(historical_data_path("1m", f"{sym}.parquet")) for sym in ["SPY", "QQQ"]],
        start_date="2025-06-03",
        end_date="2025-06-03",
        trading_mode="AGGRESSIVE",
        trade_types=["DAILY", "SCALP"],
        export_market_state=True,
        htf_warmup_days=warmup_days  # KEY PARAMETER
    )
    
    engine = BacktestEngine(config)
    engine.load_data()
    result = engine.run()
    
    print(f"✅ Backtest complete")
    print(f"  Bars: {result.total_bars}")
    print(f"  Setups: {len(engine.all_generated_setups)}")
    print(f"  Trades: {result.total_trades}")
    
    # Analyze
    if engine.market_state_records:
        df = pd.DataFrame(engine.market_state_records)
        
        # day_type distribution
        day_type_counts = Counter(df['day_type'])
        total = len(df)
        unknown_count = day_type_counts.get('unknown', 0)
        unknown_pct = round(unknown_count / total * 100, 1) if total > 0 else 100.0
        
        # daily_structure distribution
        struct_counts = Counter(df['daily_structure'])
        struct_unknown = struct_counts.get('unknown', 0)
        struct_unknown_pct = round(struct_unknown / total * 100, 1) if total > 0 else 100.0
        
        print(f"\n📊 Results:")
        print(f"  day_type unknown: {unknown_count}/{total} ({unknown_pct}%)")
        print(f"  daily_structure unknown: {struct_unknown}/{total} ({struct_unknown_pct}%)")
        
        return {
            "label": label,
            "warmup_days": warmup_days,
            "total_setups": len(engine.all_generated_setups),
            "total_records": total,
            "day_type_unknown_count": unknown_count,
            "day_type_unknown_pct": unknown_pct,
            "daily_structure_unknown_count": struct_unknown,
            "daily_structure_unknown_pct": struct_unknown_pct,
            "day_type_distribution": dict(day_type_counts),
            "daily_structure_distribution": dict(struct_counts),
        }
    else:
        print("\n⚠️  No market_state records")
        return None


def main():
    """Run before/after comparison."""
    
    print("=" * 80)
    print("P2-2.B B3 - HTF WARMUP VALIDATION (BEFORE/AFTER)")
    print("=" * 80)
    
    # BEFORE: No warmup
    before = run_audit(warmup_days=0, label="before")
    
    # AFTER: 30 days warmup
    after = run_audit(warmup_days=30, label="after")
    
    # Compare
    print(f"\n{'='*80}")
    print("COMPARISON")
    print(f"{'='*80}\n")
    
    if before and after:
        # day_type unknown rate
        delta_unknown = before["day_type_unknown_pct"] - after["day_type_unknown_pct"]
        
        print(f"day_type Unknown Rate:")
        print(f"  Before: {before['day_type_unknown_pct']:.1f}%")
        print(f"  After:  {after['day_type_unknown_pct']:.1f}%")
        print(f"  Delta:  {delta_unknown:+.1f}% ({'+' if delta_unknown > 0 else ''}{delta_unknown:.1f} percentage points)")
        
        # daily_structure unknown rate
        delta_struct = before["daily_structure_unknown_pct"] - after["daily_structure_unknown_pct"]
        
        print(f"\ndaily_structure Unknown Rate:")
        print(f"  Before: {before['daily_structure_unknown_pct']:.1f}%")
        print(f"  After:  {after['daily_structure_unknown_pct']:.1f}%")
        print(f"  Delta:  {delta_struct:+.1f}%")
        
        # Save results
        comparison = {
            "date": "2025-06-03",
            "before": before,
            "after": after,
            "delta": {
                "day_type_unknown_pct": delta_unknown,
                "daily_structure_unknown_pct": delta_struct,
            }
        }
        
        output_path = results_path("day_type_warmup_before_after_2025-06-03.json")
        with open(output_path, 'w') as f:
            json.dump(comparison, f, indent=2)
        print(f"\n✅ Saved: {output_path}")
        
        # Verdict
        print(f"\n{'='*80}")
        print("VERDICT")
        print(f"{'='*80}\n")
        
        if delta_unknown > 50:
            print(f"✅ SUCCESS: day_type unknown rate reduced by {delta_unknown:.1f}%")
            print(f"   Warmup patch EFFECTIVE")
        elif delta_unknown > 0:
            print(f"⚠️  PARTIAL: day_type unknown rate reduced by {delta_unknown:.1f}%")
            print(f"   Warmup patch helps but more investigation needed")
        else:
            print(f"❌ FAILED: day_type unknown rate did NOT improve")
            print(f"   Warmup patch ineffective or other issue")
        
        print(f"\n{'='*80}")
    else:
        print("\n❌ Comparison failed (missing data)")


if __name__ == "__main__":
    main()
