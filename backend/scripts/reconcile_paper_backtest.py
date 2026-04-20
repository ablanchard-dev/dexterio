"""Paper-vs-backtest reconcile harness.

Given a backtest trades parquet (produced with IdealFillModel — default
ExecutionEngine), replay each trade's entry and exit with ConservativeFillModel
and report the per-trade fill-price delta plus the aggregate portfolio impact.

What it answers: **if we promote this portfolio to paper trading, how much
slippage should we expect on top of the backtest's already-costed P&L?**

Method (per trade):
  - Load 1m bars for the trade's symbol.
  - Locate bar_entry = last 1m bar at/before timestamp_entry.
  - Locate bar_exit  = last 1m bar at/before timestamp_exit.
  - next_bar_entry = bar AFTER bar_entry (chronologically).
  - next_bar_exit  = bar AFTER bar_exit.
  - Conservative entry price: next_bar_entry.open with adverse slippage (buy→higher, sell→lower).
  - Conservative exit price:  next_bar_exit.open  with adverse slippage (sell→lower, buy→higher).
  - Delta_dollars = (gross_conservative - gross_ideal).

Reports:
  - Per-trade table with ideal entry/exit, conservative entry/exit, delta_$.
  - Aggregate: count, sum_delta_$, mean_delta_$, p50/p95 delta_$, mean_delta_R.

Usage:
  .venv/bin/python backend/scripts/reconcile_paper_backtest.py \\
      backend/results/labs/mini_week/calib_corpus_v1/oct_w2/trades_*.parquet \\
      [--slippage-pct 0.0005] [--out report.md]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

import pandas as pd


def _load_bars(symbol: str, bars_dir: Path) -> pd.DataFrame:
    fp = bars_dir / f"{symbol}_1m.parquet"
    if not fp.exists():
        raise FileNotFoundError(f"1m bars not found: {fp}")
    df = pd.read_parquet(fp)
    ts_col = "datetime" if "datetime" in df.columns else "timestamp"
    df[ts_col] = pd.to_datetime(df[ts_col], utc=True)
    df = df.sort_values(ts_col).reset_index(drop=True)
    df = df.rename(columns={ts_col: "ts"})
    return df


def _bar_at_or_before(bars: pd.DataFrame, ts: pd.Timestamp) -> Optional[int]:
    """Return the index of the last bar whose ts <= target, or None."""
    # searchsorted with side='right' gives insertion index; we want the last <=, so subtract 1
    idx = bars["ts"].searchsorted(ts, side="right") - 1
    if idx < 0:
        return None
    return int(idx)


def _adverse(price: float, side: str, slippage_pct: float) -> float:
    """side='buy' → price up (adverse). side='sell' → price down (adverse)."""
    if side == "buy":
        return price * (1.0 + slippage_pct)
    return price * (1.0 - slippage_pct)


def reconcile(trades_path: Path, bars_dir: Path,
              slippage_pct: float = 0.0005) -> pd.DataFrame:
    trades = pd.read_parquet(trades_path)
    trades["timestamp_entry"] = pd.to_datetime(trades["timestamp_entry"], utc=True)
    trades["timestamp_exit"] = pd.to_datetime(trades["timestamp_exit"], utc=True)

    bars_cache: dict[str, pd.DataFrame] = {}

    rows = []
    skipped = 0
    for _, tr in trades.iterrows():
        sym = tr["symbol"]
        if sym not in bars_cache:
            bars_cache[sym] = _load_bars(sym, bars_dir)
        bars = bars_cache[sym]

        i_entry = _bar_at_or_before(bars, tr["timestamp_entry"])
        i_exit = _bar_at_or_before(bars, tr["timestamp_exit"])
        if i_entry is None or i_exit is None:
            skipped += 1
            continue
        # Conservative: use the NEXT 1m bar's open
        if i_entry + 1 >= len(bars) or i_exit + 1 >= len(bars):
            skipped += 1
            continue
        next_entry = bars.iloc[i_entry + 1]
        next_exit = bars.iloc[i_exit + 1]

        direction = tr["direction"]
        size = float(tr["position_size"])
        ideal_entry = float(tr["entry_price"])
        ideal_exit = float(tr["exit_price"])

        # Entry: LONG buys (adverse = price up); SHORT sells (adverse = price down)
        entry_side = "buy" if direction == "LONG" else "sell"
        exit_side = "sell" if direction == "LONG" else "buy"

        cons_entry = _adverse(float(next_entry["open"]), entry_side, slippage_pct)
        cons_exit = _adverse(float(next_exit["open"]), exit_side, slippage_pct)

        # Gross P&L dollars (no costs, just fill delta)
        dir_sign = 1.0 if direction == "LONG" else -1.0
        gross_ideal = (ideal_exit - ideal_entry) * size * dir_sign
        gross_cons = (cons_exit - cons_entry) * size * dir_sign
        delta_dollars = gross_cons - gross_ideal

        # Per-R delta (use trade's risk_dollars if present)
        risk_d = float(tr.get("risk_dollars", 0.0) or 0.0)
        delta_r = delta_dollars / risk_d if risk_d > 0 else 0.0

        rows.append({
            "trade_id": tr["trade_id"],
            "symbol": sym,
            "direction": direction,
            "playbook": tr.get("playbook"),
            "exit_reason": tr.get("exit_reason"),
            "size": size,
            "ideal_entry": ideal_entry,
            "conservative_entry": round(cons_entry, 4),
            "ideal_exit": ideal_exit,
            "conservative_exit": round(cons_exit, 4),
            "gross_ideal_$": round(gross_ideal, 2),
            "gross_conservative_$": round(gross_cons, 2),
            "delta_$": round(delta_dollars, 2),
            "delta_R": round(delta_r, 4),
        })

    print(f"Reconciled {len(rows)} trades (skipped {skipped} for bar-edge issues)", file=sys.stderr)
    return pd.DataFrame(rows)


def summarize(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"n": 0}
    return {
        "n_trades": len(df),
        "total_delta_$": round(df["delta_$"].sum(), 2),
        "mean_delta_$": round(df["delta_$"].mean(), 2),
        "p50_delta_$": round(df["delta_$"].quantile(0.5), 2),
        "p95_delta_$": round(df["delta_$"].quantile(0.95), 2),
        "min_delta_$": round(df["delta_$"].min(), 2),
        "max_delta_$": round(df["delta_$"].max(), 2),
        "total_delta_R": round(df["delta_R"].sum(), 3),
        "mean_delta_R": round(df["delta_R"].mean(), 4),
        "pct_trades_worse": round((df["delta_$"] < 0).mean() * 100, 1),
    }


def write_report(df: pd.DataFrame, summary: dict, out_path: Path,
                 trades_path: Path, slippage_pct: float) -> None:
    lines = []
    lines.append(f"# Paper-vs-backtest reconcile — {trades_path.name}\n")
    lines.append(f"**Slippage model:** ConservativeFillModel, {slippage_pct * 100:.3f}% adverse slippage on next-bar-open fills.\n")
    lines.append("**Interpretation:** negative delta_$ = conservative model would have been worse than the backtest's ideal fill.\n")
    lines.append("## Aggregate\n")
    lines.append("| metric | value |")
    lines.append("|---|---|")
    for k, v in summary.items():
        lines.append(f"| {k} | {v} |")
    lines.append("")
    lines.append("## First 20 trades\n")
    cols = ["trade_id", "symbol", "direction", "playbook", "exit_reason",
            "ideal_entry", "conservative_entry", "ideal_exit", "conservative_exit",
            "delta_$", "delta_R"]
    lines.append("| " + " | ".join(cols) + " |")
    lines.append("|" + "|".join(["---"] * len(cols)) + "|")
    for _, r in df.head(20).iterrows():
        vals = [str(r[c]) for c in cols]
        lines.append("| " + " | ".join(vals) + " |")
    out_path.write_text("\n".join(lines))
    print(f"Report: {out_path}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("trades_parquet", type=Path)
    ap.add_argument("--bars-dir", type=Path,
                    default=Path(__file__).resolve().parents[1] / "data/market")
    ap.add_argument("--slippage-pct", type=float, default=0.0005,
                    help="adverse slippage on next-bar-open fills (default 0.05%%)")
    ap.add_argument("--out", type=Path, default=None,
                    help="write markdown report to this path")
    args = ap.parse_args()

    df = reconcile(args.trades_parquet, args.bars_dir, args.slippage_pct)
    summary = summarize(df)
    print("\n=== Aggregate ===")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    if args.out:
        write_report(df, summary, args.out, args.trades_parquet, args.slippage_pct)
    else:
        print("\n=== First 10 trades ===")
        print(df.head(10).to_string())


if __name__ == "__main__":
    main()
