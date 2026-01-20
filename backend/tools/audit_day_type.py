#!/usr/bin/env python3
"""
P2-2.B Step B1 - day_type Audit

Audit complet:
1. Distribution day_type (unknown / trend / range / manipulation_reversal)
2. News_Fade rejections (news_events_day_type_mismatch)
3. Par symbole, par journée
"""
import sys
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter

_backend_dir = Path(__file__).parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from models.backtest import BacktestConfig
from backtest.engine import BacktestEngine
from utils.path_resolver import historical_data_path, results_path


def audit_day_type_distribution(start_date: str, end_date: str):
    """Audit day_type distribution sur période."""
    
    print(f"{'='*80}")
    print(f"day_type Distribution Audit: {start_date} → {end_date}")
    print(f"{'='*80}\n")
    
    config = BacktestConfig(
        run_name="day_type_audit",
        symbols=["SPY", "QQQ"],
        data_paths=[str(historical_data_path("1m", f"{sym}.parquet")) for sym in ["SPY", "QQQ"]],
        start_date=start_date,
        end_date=end_date,
        trading_mode="AGGRESSIVE",
        trade_types=["DAILY", "SCALP"]
    )
    
    engine = BacktestEngine(config)
    engine.load_data()
    result = engine.run()
    
    # Collecter day_type de tous les setups générés
    day_types_all = []
    day_types_by_symbol = defaultdict(list)
    day_types_by_date = defaultdict(list)
    
    for setup in engine.all_generated_setups:
        # Setup has direct attributes, not market_state
        dt = getattr(setup, 'day_type', 'unknown')
        day_types_all.append(dt)
        day_types_by_symbol[setup.symbol].append(dt)
        
        date_key = setup.timestamp.strftime('%Y-%m-%d')
        day_types_by_date[date_key].append(dt)
    
    # Distribution globale
    distribution_global = Counter(day_types_all)
    total_setups = len(day_types_all)
    
    distribution = {
        "period": f"{start_date} → {end_date}",
        "total_setups": total_setups,
        "distribution": {
            dt: {
                "count": count,
                "percentage": round(count / total_setups * 100, 2)
            }
            for dt, count in distribution_global.items()
        },
        "by_symbol": {
            symbol: {
                "total": len(dts),
                "distribution": dict(Counter(dts))
            }
            for symbol, dts in day_types_by_symbol.items()
        },
        "by_date": {
            date: {
                "total": len(dts),
                "distribution": dict(Counter(dts)),
                "unknown_pct": round(dts.count("unknown") / len(dts) * 100, 2)
            }
            for date, dts in sorted(day_types_by_date.items())
        }
    }
    
    # Top 10 jours 100% unknown
    unknown_days = [
        (date, stats["unknown_pct"])
        for date, stats in distribution["by_date"].items()
        if stats["unknown_pct"] >= 95.0
    ]
    unknown_days.sort(key=lambda x: x[1], reverse=True)
    distribution["top_unknown_days"] = unknown_days[:10]
    
    # Display
    print(f"Total Setups: {total_setups}")
    print(f"\nGlobal Distribution:")
    for dt, stats in distribution["distribution"].items():
        print(f"  {dt:25s}: {stats['count']:4d} ({stats['percentage']:5.1f}%)")
    
    print(f"\nBy Symbol:")
    for symbol, stats in distribution["by_symbol"].items():
        unknown_count = stats["distribution"].get("unknown", 0)
        unknown_pct = round(unknown_count / stats["total"] * 100, 1)
        print(f"  {symbol}: {unknown_count}/{stats['total']} unknown ({unknown_pct}%)")
    
    print(f"\nTop Unknown Days (≥95% unknown):")
    for i, (date, pct) in enumerate(distribution["top_unknown_days"][:5], 1):
        print(f"  {i}. {date}: {pct:.1f}% unknown")
    
    return distribution


def audit_news_fade_rejections(start_date: str, end_date: str):
    """Audit News_Fade rejections."""
    
    print(f"\n{'='*80}")
    print(f"News_Fade Rejection Audit: {start_date} → {end_date}")
    print(f"{'='*80}\n")
    
    config = BacktestConfig(
        run_name="news_fade_audit",
        symbols=["SPY", "QQQ"],
        data_paths=[str(historical_data_path("1m", f"{sym}.parquet")) for sym in ["SPY", "QQQ"]],
        start_date=start_date,
        end_date=end_date,
        trading_mode="AGGRESSIVE",
        trade_types=["DAILY", "SCALP"]
    )
    
    engine = BacktestEngine(config)
    engine.load_data()
    result = engine.run()
    
    # Collecter rejections
    news_fade_rejections = []
    news_fade_matches = []
    
    for setup in engine.all_generated_setups:
        # Check si playbook évalué était News_Fade
        for match in setup.playbook_matches:
            if "News" in match.playbook_name or "Fade" in match.playbook_name:
                news_fade_matches.append({
                    "date": setup.timestamp.strftime('%Y-%m-%d'),
                    "symbol": setup.symbol,
                    "playbook": match.playbook_name,
                    "score": match.score,
                    "passed": match.passes_all_gates
                })
        
        # Check rejections (depuis reason_codes si disponible)
        if hasattr(setup, 'playbook_evaluation_reasons'):
            for playbook_name, reasons in setup.playbook_evaluation_reasons.items():
                if "News" in playbook_name or "Fade" in playbook_name:
                    for reason in reasons:
                        if "day_type" in reason.lower() or "news_events" in reason.lower():
                            news_fade_rejections.append({
                                "date": setup.timestamp.strftime('%Y-%m-%d'),
                                "symbol": setup.symbol,
                                "playbook": playbook_name,
                                "reason": reason,
                                "day_type_actual": getattr(setup, 'day_type', 'unknown')
                            })
    
    audit = {
        "period": f"{start_date} → {end_date}",
        "news_fade_matches": len(news_fade_matches),
        "news_fade_rejections": len(news_fade_rejections),
        "rejection_details": news_fade_rejections[:20],  # Top 20
        "match_details": news_fade_matches[:10],  # Top 10
        "rejection_by_reason": Counter([r["reason"] for r in news_fade_rejections]),
        "rejection_by_date": Counter([r["date"] for r in news_fade_rejections]),
    }
    
    print(f"News_Fade Matches: {len(news_fade_matches)}")
    print(f"News_Fade Rejections: {len(news_fade_rejections)}")
    
    if news_fade_rejections:
        print(f"\nTop Rejection Reasons:")
        for reason, count in audit["rejection_by_reason"].most_common(5):
            print(f"  {reason}: {count}")
        
        print(f"\nTop Rejection Dates:")
        for date, count in audit["rejection_by_date"].most_common(5):
            print(f"  {date}: {count}")
    
    return audit


def main():
    """Run complete day_type audit."""
    
    print("=" * 80)
    print("P2-2.B STEP B1 - day_type + News_Fade AUDIT")
    print("=" * 80)
    print()
    
    # Audit sur 5 jours (sample représentatif, rapide)
    start_date = "2025-06-03"
    end_date = "2025-06-09"
    
    print(f"Strategy: 5-day sample audit (faster, representative)")
    print()
    
    # 1. day_type distribution
    day_type_dist = audit_day_type_distribution(start_date, end_date)
    
    # Save
    output_path = results_path("day_type_distribution_5d_sample.json")
    with open(output_path, 'w') as f:
        json.dump(day_type_dist, f, indent=2)
    print(f"\n✅ Saved: {output_path}")
    
    # 2. News_Fade rejections
    news_fade_audit = audit_news_fade_rejections(start_date, end_date)
    
    # Save
    output_path = results_path("news_fade_rejection_audit_5d_sample.json")
    with open(output_path, 'w') as f:
        json.dump(news_fade_audit, f, indent=2, default=str)
    print(f"✅ Saved: {output_path}")
    
    # Summary
    print(f"\n{'='*80}")
    print("AUDIT SUMMARY")
    print(f"{'='*80}")
    
    unknown_pct = day_type_dist["distribution"].get("unknown", {}).get("percentage", 0)
    print(f"\nday_type Unknown: {unknown_pct:.1f}%")
    print(f"News_Fade Rejections: {news_fade_audit['news_fade_rejections']}")
    
    if unknown_pct > 50:
        print(f"\n⚠️  HIGH UNKNOWN RATE (>{unknown_pct:.0f}%)")
        print(f"   Root cause investigation needed (Step B2)")
    
    print(f"\n{'='*80}")


if __name__ == "__main__":
    main()
