"""
Phase 1C — Ablation analysis on NY_Open_Reversal (and all playbooks).

Analyzes existing WF trade parquets to find edge-carrying conditions:
- By grade (A+, A, B, C)
- By hour of day
- By month
- By exit_reason (SL, TP, session_end)
- By direction (LONG vs SHORT)
- By symbol (SPY vs QQQ)

Usage:
    cd backend && python -m scripts.ablation_ny_analysis
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime


RESULTS_DIR = Path(__file__).resolve().parent.parent / "results" / "labs" / "mini_week" / "phase1_wf_all"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "results" / "labs" / "ablation_phase1"


def load_all_trades() -> pd.DataFrame:
    """Load and merge trades from both WF folds."""
    parquets = sorted(RESULTS_DIR.glob("phase1_s*/trades_*.parquet"))
    if not parquets:
        raise FileNotFoundError(f"No trade parquets found in {RESULTS_DIR}")

    dfs = []
    for p in parquets:
        df = pd.read_parquet(p)
        fold = "s0_jun_aug" if "s0" in p.name else "s1_sep_nov"
        df["fold"] = fold
        dfs.append(df)

    trades = pd.concat(dfs, ignore_index=True)
    trades["timestamp_entry"] = pd.to_datetime(trades["timestamp_entry"], utc=True)
    trades["hour"] = trades["timestamp_entry"].dt.hour
    return trades


def metrics(df: pd.DataFrame) -> dict:
    """Compute standard metrics for a slice of trades."""
    n = len(df)
    if n == 0:
        return {"trades": 0, "E[R]": None, "WR": None, "PF": None, "sum_R": None}

    wins = df[df["r_multiple"] > 0]
    losses = df[df["r_multiple"] <= 0]
    gross_profit = wins["r_multiple"].sum() if len(wins) > 0 else 0.0
    gross_loss = abs(losses["r_multiple"].sum()) if len(losses) > 0 else 0.0

    return {
        "trades": n,
        "E[R]": round(df["r_multiple"].mean(), 4),
        "WR": round(len(wins) / n * 100, 1),
        "PF": round(gross_profit / gross_loss, 3) if gross_loss > 0 else float("inf"),
        "sum_R": round(df["r_multiple"].sum(), 2),
    }


def ablation_by(trades: pd.DataFrame, col: str, playbook_filter: str = None) -> dict:
    """Run ablation slicing trades by a given column."""
    if playbook_filter:
        trades = trades[trades["playbook"] == playbook_filter]

    results = {}
    for val, group in trades.groupby(col):
        results[str(val)] = metrics(group)

    # Add total
    results["_TOTAL"] = metrics(trades)
    return results


def run_full_ablation(trades: pd.DataFrame) -> dict:
    """Run comprehensive ablation on all dimensions."""
    report = {}

    # Global by playbook
    report["by_playbook"] = ablation_by(trades, "playbook")

    # NY_Open_Reversal deep dive
    ny = trades[trades["playbook"] == "NY_Open_Reversal"]
    report["NY_Open_Reversal"] = {
        "by_grade": ablation_by(ny, "match_grade"),
        "by_hour": ablation_by(ny, "hour"),
        "by_month": ablation_by(ny, "month"),
        "by_exit_reason": ablation_by(ny, "exit_reason"),
        "by_direction": ablation_by(ny, "direction"),
        "by_symbol": ablation_by(ny, "symbol"),
        "by_fold": ablation_by(ny, "fold"),
    }

    # Same for IFVG_5m_Sweep (2nd best PF)
    ifvg = trades[trades["playbook"] == "IFVG_5m_Sweep"]
    if len(ifvg) > 0:
        report["IFVG_5m_Sweep"] = {
            "by_grade": ablation_by(ifvg, "match_grade"),
            "by_hour": ablation_by(ifvg, "hour"),
            "by_month": ablation_by(ifvg, "month"),
            "by_exit_reason": ablation_by(ifvg, "exit_reason"),
            "by_direction": ablation_by(ifvg, "direction"),
            "by_symbol": ablation_by(ifvg, "symbol"),
        }

    # Cross-playbook: grade A+ and A only
    high_grade = trades[trades["match_grade"].isin(["A+", "A"])]
    report["high_grade_only"] = ablation_by(high_grade, "playbook")

    # Time window analysis: first 30 min vs rest (convert UTC → ET: subtract 4h for EDT)
    trades_copy = trades.copy()
    trades_copy["hour_et"] = (trades_copy["hour"] - 4) % 24  # UTC to ET (EDT)
    trades_copy["minute_from_open"] = trades_copy["timestamp_entry"].dt.minute + (trades_copy["hour_et"] - 9) * 60
    trades_copy["time_bucket"] = trades_copy["minute_from_open"].apply(
        lambda m: "first_30min" if m <= 30 else ("10h_slot" if m <= 90 else ("mid_morning" if m <= 150 else "afternoon"))
    )
    report["by_time_bucket"] = ablation_by(trades_copy, "time_bucket")

    return report


def print_section(title: str, data: dict):
    """Pretty print a section of ablation results."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")
    print(f"  {'Slice':<20} {'Trades':>7} {'E[R]':>8} {'WR':>7} {'PF':>7} {'Sum R':>8}")
    print(f"  {'-'*60}")
    for k, v in sorted(data.items()):
        if v["trades"] == 0:
            continue
        er = f"{v['E[R]']:+.4f}" if v["E[R]"] is not None else "N/A"
        wr = f"{v['WR']:.1f}%" if v["WR"] is not None else "N/A"
        pf = f"{v['PF']:.3f}" if v["PF"] is not None and v["PF"] != float("inf") else "inf"
        sr = f"{v['sum_R']:+.2f}" if v["sum_R"] is not None else "N/A"
        label = "_TOTAL" if k == "_TOTAL" else k
        print(f"  {label:<20} {v['trades']:>7} {er:>8} {wr:>7} {pf:>7} {sr:>8}")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading trades from WF folds...")
    trades = load_all_trades()
    print(f"Total trades: {len(trades)}")
    print(f"Playbooks: {trades['playbook'].unique().tolist()}")

    report = run_full_ablation(trades)

    # Print results
    print_section("BY PLAYBOOK (all trades)", report["by_playbook"])

    for section in ["by_grade", "by_hour", "by_month", "by_exit_reason", "by_direction", "by_symbol", "by_fold"]:
        print_section(f"NY_Open_Reversal — {section}", report["NY_Open_Reversal"][section])

    if "IFVG_5m_Sweep" in report:
        for section in ["by_grade", "by_hour", "by_exit_reason"]:
            print_section(f"IFVG_5m_Sweep — {section}", report["IFVG_5m_Sweep"][section])

    print_section("HIGH GRADE ONLY (A+/A) by playbook", report["high_grade_only"])
    print_section("BY TIME BUCKET (all playbooks)", report["by_time_bucket"])

    # Save JSON
    out_path = OUTPUT_DIR / "ablation_phase1_report.json"
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nReport saved: {out_path}")


if __name__ == "__main__":
    main()
