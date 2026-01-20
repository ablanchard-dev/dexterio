#!/usr/bin/env python3
"""
P2-2.B B1 - Instrumented 1D Audit

Run 1D backtest avec export market_state pour audit day_type.
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


def run_instrumented_backtest():
    """Run 1D with market_state export."""
    
    print("="*80)
    print("P2-2.B B1 - INSTRUMENTED 1D BACKTEST")
    print("="*80)
    print()
    
    # Config
    config = BacktestConfig(
        run_name="day_type_audit_1d",
        symbols=["SPY", "QQQ"],
        data_paths=[str(historical_data_path("1m", f"{sym}.parquet")) for sym in ["SPY", "QQQ"]],
        start_date="2025-06-03",
        end_date="2025-06-03",
        trading_mode="AGGRESSIVE",
        trade_types=["DAILY", "SCALP"],
        export_market_state=True  # Enable export
    )
    
    # Run
    engine = BacktestEngine(config)
    engine.load_data()
    result = engine.run()
    
    print(f"\n✅ Backtest complete")
    print(f"  Bars: {result.total_bars}")
    print(f"  Trades: {result.total_trades}")
    print(f"  Setups: {len(engine.all_generated_setups)}")
    print(f"  Market state records: {len(engine.market_state_records) if engine.market_state_records else 0}")
    
    # Export market_state stream
    if engine.market_state_records:
        df = pd.DataFrame(engine.market_state_records)
        output_path = results_path("market_state_stream_2025-06-03_SPY_QQQ.parquet")
        df.to_parquet(output_path, index=False)
        print(f"\n✅ Market state stream exported: {output_path}")
        print(f"  Records: {len(df)}")
        
        return df, engine
    else:
        print("\n⚠️  No market_state records (export not enabled)")
        return None, engine


def analyze_day_type(df: pd.DataFrame):
    """Analyze day_type distribution."""
    
    print(f"\n{'='*80}")
    print("day_type DISTRIBUTION ANALYSIS")
    print(f"{'='*80}\n")
    
    # Global distribution
    day_type_counts = Counter(df['day_type'])
    total = len(df)
    
    distribution = {
        "period": "2025-06-03",
        "total_records": total,
        "distribution": {
            dt: {
                "count": count,
                "percentage": round(count / total * 100, 2)
            }
            for dt, count in day_type_counts.items()
        },
        "by_symbol": {}
    }
    
    print(f"Total Records: {total}")
    print(f"\nGlobal Distribution:")
    for dt, stats in sorted(distribution["distribution"].items(), key=lambda x: -x[1]["count"]):
        print(f"  {dt:25s}: {stats['count']:4d} ({stats['percentage']:5.1f}%)")
    
    # By symbol
    for symbol in df['symbol'].unique():
        symbol_df = df[df['symbol'] == symbol]
        symbol_dist = Counter(symbol_df['day_type'])
        distribution["by_symbol"][symbol] = {
            "total": len(symbol_df),
            "distribution": dict(symbol_dist)
        }
        
        unknown_count = symbol_dist.get('unknown', 0)
        unknown_pct = round(unknown_count / len(symbol_df) * 100, 1)
        print(f"\n{symbol}:")
        print(f"  Total: {len(symbol_df)}")
        print(f"  Unknown: {unknown_count} ({unknown_pct}%)")
    
    # daily_structure analysis
    if 'daily_structure' in df.columns:
        print(f"\ndaily_structure Distribution:")
        struct_counts = Counter(df['daily_structure'])
        for struct, count in sorted(struct_counts.items(), key=lambda x: -x[1]):
            pct = round(count / total * 100, 1)
            print(f"  {struct:20s}: {count:4d} ({pct:5.1f}%)")
    
    return distribution


def analyze_news_fade(engine):
    """Analyze News_Fade rejections."""
    
    print(f"\n{'='*80}")
    print("News_Fade REJECTION ANALYSIS")
    print(f"{'='*80}\n")
    
    news_fade_matches = 0
    news_fade_rejections = []
    
    # Scan setups for News_Fade playbook
    for setup in engine.all_generated_setups:
        # Check if any playbook match is News_Fade related
        for match in setup.playbook_matches:
            if "News" in match.playbook_name or "Fade" in match.playbook_name:
                news_fade_matches += 1
        
        # TODO: Check rejection reasons if available
        # For now, proxy: if day_type = unknown and no matches, likely rejected
    
    audit = {
        "period": "2025-06-03",
        "total_setups": len(engine.all_generated_setups),
        "news_fade_matches": news_fade_matches,
        "notes": "Full rejection tracking requires playbook_evaluation_reasons instrumentation"
    }
    
    print(f"Total Setups: {audit['total_setups']}")
    print(f"News_Fade Matches: {news_fade_matches}")
    
    if news_fade_matches == 0:
        print(f"\n⚠️  NO News_Fade matches found")
        print(f"   Likely cause: day_type mismatch or other gating rejection")
    
    return audit


def main():
    """Run instrumented audit."""
    
    # Run backtest with export
    df, engine = run_instrumented_backtest()
    
    if df is None:
        print("\n❌ No market_state data exported")
        return
    
    # Analyze
    day_type_dist = analyze_day_type(df)
    news_fade_audit = analyze_news_fade(engine)
    
    # Save results
    output_dist = results_path("day_type_distribution_1d_sample.json")
    with open(output_dist, 'w') as f:
        json.dump(day_type_dist, f, indent=2)
    print(f"\n✅ Saved: {output_dist}")
    
    output_news = results_path("news_fade_rejection_audit_1d_sample.json")
    with open(output_news, 'w') as f:
        json.dump(news_fade_audit, f, indent=2)
    print(f"✅ Saved: {output_news}")
    
    # Summary
    unknown_pct = day_type_dist["distribution"].get("unknown", {}).get("percentage", 0)
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"\nday_type Unknown Rate: {unknown_pct:.1f}%")
    
    if unknown_pct > 70:
        print(f"\n⚠️  CRITICAL: {unknown_pct:.0f}% unknown rate")
        print(f"   → HTF wiring issue probable")
        print(f"   → Next: B2 root cause investigation")
    elif unknown_pct > 30:
        print(f"\n⚠️  HIGH unknown rate ({unknown_pct:.0f}%)")
        print(f"   → Partial HTF data or warmup needed")
    else:
        print(f"\n✅ Acceptable unknown rate ({unknown_pct:.0f}%)")
    
    print(f"\n{'='*80}")


if __name__ == "__main__":
    main()
