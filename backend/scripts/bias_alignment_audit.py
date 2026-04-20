"""
Bias alignment audit (Phase D pre-work, signal redesign / detector audit).

Question: when trades fire, are they aligned with D/4H bias? If not, does
the bias-aligned subset have edge that the bias-counter subset lacks?

Method (simple, defensible proxy):
  - D bias at trade entry T = sign(close_D[T-1] - SMA_D_5[T-1])
    bullish if close > SMA, bearish if below, neutral if within tolerance
  - 4H bias at T = sign(close_4H[T-1] - SMA_4H_5[T-1])
  - Trade aligned with X-bias iff (X bullish AND direction=LONG) OR
    (X bearish AND direction=SHORT). Counter is the opposite. Neutral
    bias trades excluded from alignment metric (kept in N).

Inputs: any glob of trades_*.parquet (default = survivor_v1 corpus).
Output: stdout report only (read-only audit).

Usage:
  python -m backend.scripts.bias_alignment_audit \\
    --corpus backend/results/labs/mini_week/survivor_v1
"""
from __future__ import annotations

import argparse
import glob
import os
import sys
from typing import Tuple

import numpy as np
import pandas as pd


def load_trades(corpus_dir: str) -> pd.DataFrame:
    parts = []
    for f in sorted(glob.glob(os.path.join(corpus_dir, "*", "trades_*.parquet"))):
        d = pd.read_parquet(f)
        d["__src"] = os.path.basename(os.path.dirname(f))
        parts.append(d)
    if not parts:
        sys.exit(f"No trades found under {corpus_dir}")
    df = pd.concat(parts, ignore_index=True)
    df["timestamp_entry"] = pd.to_datetime(df["timestamp_entry"], utc=True).astype("datetime64[ns, UTC]")
    return df


def load_bars(symbol: str, market_dir: str) -> pd.DataFrame:
    f = os.path.join(market_dir, f"{symbol}_1m.parquet")
    bars = pd.read_parquet(f)
    bars["datetime"] = pd.to_datetime(bars["datetime"], utc=True)
    bars = bars.set_index("datetime").sort_index()
    return bars[["open", "high", "low", "close"]]


def resample_with_bias(bars: pd.DataFrame, rule: str, sma_n: int = 5) -> pd.DataFrame:
    """Return per-period close + SMA + bias flag, forward-filled to per-minute."""
    agg = bars.resample(rule, label="right", closed="right").agg({"close": "last"}).dropna()
    agg["sma"] = agg["close"].rolling(sma_n, min_periods=sma_n).mean()
    agg["bias"] = np.where(
        agg["close"] > agg["sma"], "bull",
        np.where(agg["close"] < agg["sma"], "bear", "neutral"),
    )
    return agg


def attach_bias(trades: pd.DataFrame, bars_by_sym: dict) -> pd.DataFrame:
    """For each trade, look up D-bias and 4H-bias at T-ε (last close prior to entry)."""
    out_rows = []
    cache = {}
    for sym, bars in bars_by_sym.items():
        cache[(sym, "D")] = resample_with_bias(bars, "1D", sma_n=5)
        cache[(sym, "4H")] = resample_with_bias(bars, "4h", sma_n=5)

    for sym, sub in trades.groupby("symbol"):
        d_tab = cache[(sym, "D")].reset_index().rename(columns={"datetime": "ts"})
        h4_tab = cache[(sym, "4H")].reset_index().rename(columns={"datetime": "ts"})
        d_tab["ts"] = d_tab["ts"].astype("datetime64[ns, UTC]")
        h4_tab["ts"] = h4_tab["ts"].astype("datetime64[ns, UTC]")
        sub_s = sub.sort_values("timestamp_entry").reset_index(drop=True)
        # merge_asof: for each entry, take the most recent bar <= entry
        d_join = pd.merge_asof(
            sub_s[["timestamp_entry", "trade_id"]].rename(columns={"timestamp_entry": "ts"}),
            d_tab.rename(columns={"close": "d_close", "sma": "d_sma", "bias": "d_bias"}),
            on="ts", direction="backward",
        )
        h4_join = pd.merge_asof(
            sub_s[["timestamp_entry", "trade_id"]].rename(columns={"timestamp_entry": "ts"}),
            h4_tab.rename(columns={"close": "h4_close", "sma": "h4_sma", "bias": "h4_bias"}),
            on="ts", direction="backward",
        )
        merged = sub_s.merge(d_join[["trade_id", "d_bias"]], on="trade_id", how="left")
        merged = merged.merge(h4_join[["trade_id", "h4_bias"]], on="trade_id", how="left")
        out_rows.append(merged)
    return pd.concat(out_rows, ignore_index=True)


def alignment_label(direction: str, bias: str) -> str:
    if pd.isna(bias) or bias == "neutral":
        return "neutral"
    d = (direction or "").upper()
    if d == "LONG":
        return "aligned" if bias == "bull" else "counter"
    if d == "SHORT":
        return "aligned" if bias == "bear" else "counter"
    return "neutral"


def report_split(df: pd.DataFrame, bias_col: str, label: str) -> None:
    df = df.copy()
    df["alignment"] = [alignment_label(d, b) for d, b in zip(df["direction"], df[bias_col])]
    print(f"\n=== {label} alignment ===")
    print(f"Distribution: {df['alignment'].value_counts().to_dict()}")
    overall = df.groupby("alignment").agg(
        n=("r_multiple", "size"),
        ER=("r_multiple", "mean"),
        tot=("r_multiple", "sum"),
    ).round(3)
    print("Overall:")
    print(overall.to_string())

    print(f"\nPer playbook ({label}):")
    pb = df.groupby(["playbook", "alignment"]).agg(
        n=("r_multiple", "size"),
        ER=("r_multiple", "mean"),
        tot=("r_multiple", "sum"),
    ).round(3)
    # pivot to wide for readability
    wide_n = pb["n"].unstack(fill_value=0)
    wide_ER = pb["ER"].unstack(fill_value=np.nan)
    wide_tot = pb["tot"].unstack(fill_value=0)
    for col in ["aligned", "counter", "neutral"]:
        if col not in wide_n.columns:
            wide_n[col] = 0
            wide_ER[col] = np.nan
            wide_tot[col] = 0.0
    summary = pd.DataFrame({
        "n_aligned": wide_n["aligned"],
        "ER_aligned": wide_ER["aligned"],
        "tot_aligned": wide_tot["aligned"],
        "n_counter": wide_n["counter"],
        "ER_counter": wide_ER["counter"],
        "tot_counter": wide_tot["counter"],
        "n_neutral": wide_n["neutral"],
        "ER_neutral": wide_ER["neutral"],
    }).round(3)
    summary["delta_ER"] = (summary["ER_aligned"] - summary["ER_counter"]).round(3)
    summary = summary.sort_values("delta_ER", ascending=False, na_position="last")
    print(summary.to_string())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True, help="Corpus dir with week subfolders")
    ap.add_argument("--market", default="backend/data/market", help="Dir with SYM_1m.parquet")
    args = ap.parse_args()

    trades = load_trades(args.corpus)
    print(f"Loaded {len(trades)} trades from {args.corpus}")
    print(f"Symbols: {trades['symbol'].value_counts().to_dict()}")
    print(f"Direction: {trades['direction'].value_counts().to_dict()}")

    bars_by_sym = {sym: load_bars(sym, args.market) for sym in trades["symbol"].unique()}
    enriched = attach_bias(trades, bars_by_sym)
    print(f"\nD bias dist: {enriched['d_bias'].value_counts().to_dict()}")
    print(f"4H bias dist: {enriched['h4_bias'].value_counts().to_dict()}")

    # Combined: trade is "aligned" iff both D and 4H agree with direction
    enriched["combo_aligned"] = [
        "aligned" if alignment_label(d, db) == "aligned" and alignment_label(d, h4b) == "aligned"
        else ("counter" if alignment_label(d, db) == "counter" and alignment_label(d, h4b) == "counter"
              else "mixed")
        for d, db, h4b in zip(enriched["direction"], enriched["d_bias"], enriched["h4_bias"])
    ]

    report_split(enriched, "d_bias", "Daily")
    report_split(enriched, "h4_bias", "4H")

    print("\n=== Combined D∧4H alignment (both must agree) ===")
    print(f"Distribution: {enriched['combo_aligned'].value_counts().to_dict()}")
    print("Overall:")
    g = enriched.groupby("combo_aligned").agg(
        n=("r_multiple", "size"),
        ER=("r_multiple", "mean"),
        tot=("r_multiple", "sum"),
    ).round(3)
    print(g.to_string())
    print("\nPer playbook (combined):")
    pb = enriched.groupby(["playbook", "combo_aligned"]).agg(
        n=("r_multiple", "size"),
        ER=("r_multiple", "mean"),
        tot=("r_multiple", "sum"),
    ).round(3)
    print(pb.to_string())


if __name__ == "__main__":
    main()
