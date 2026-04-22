#!/usr/bin/env python3
"""
Post-hoc replay of entry_confirm_no_commit rejected vs passed setups.

Reads `ec_audit_<run_id>.jsonl` (emitted by engine.py at the entry_confirm
gate) and forward-replays 1m bars from each setup's timestamp to compute:
  - peak_R (best R reached before SL/horizon)
  - mae_R (worst R, always ≤ 0)
  - hit_tp / hit_sl / hit_+0.5R / hit_+1R
  - time_to_hit_tp / time_to_hit_sl

Then aggregates per `event` (rejected_no_commit vs passed) to answer:
  are rejected setups better, worse, or same as passed setups?

Intrabar priority: if both SL and TP hit on same bar → SL first (matches
engine convention, conservative for LONG winners).
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import pandas as pd
import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[2]


def load_ec_audit(path: Path) -> pd.DataFrame:
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    df = pd.DataFrame(rows)
    if "ts" in df.columns:
        df["ts"] = pd.to_datetime(df["ts"], utc=True)
    return df


def load_bars(symbol: str) -> pd.DataFrame:
    path = REPO_ROOT / f"backend/data/market/{symbol}_1m.parquet"
    df = pd.read_parquet(path)
    df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
    df = df.sort_values("datetime").reset_index(drop=True)
    return df


def replay_one(
    entry: float,
    sl: float,
    tp: float,
    direction: str,
    ts: pd.Timestamp,
    bars: pd.DataFrame,
    horizon_min: int = 300,
) -> dict:
    """Forward-replay from ts+1m for horizon_min minutes or until TP/SL hit."""
    sl_dist = abs(entry - sl)
    if sl_dist <= 0:
        return {"valid": False}

    is_long = direction == "LONG"
    start = ts + pd.Timedelta(minutes=1)
    end = ts + pd.Timedelta(minutes=horizon_min)
    win = bars[(bars["datetime"] >= start) & (bars["datetime"] <= end)]
    if len(win) == 0:
        return {"valid": False}

    peak_R = 0.0
    mae_R = 0.0
    hit_tp = False
    hit_sl = False
    hit_half = False
    hit_one = False
    t_tp = None
    t_sl = None

    for _, bar in win.iterrows():
        high = float(bar["high"])
        low = float(bar["low"])

        if is_long:
            mfe = high - entry  # best excursion
            mae = low - entry   # worst excursion (≤0)
        else:
            mfe = entry - low
            mae = entry - high

        r_peak = mfe / sl_dist
        r_mae = mae / sl_dist

        peak_R = max(peak_R, r_peak)
        mae_R = min(mae_R, r_mae)
        if r_peak >= 0.5:
            hit_half = True
        if r_peak >= 1.0:
            hit_one = True

        sl_hit_this_bar = (low <= sl) if is_long else (high >= sl)
        tp_hit_this_bar = (high >= tp) if is_long else (low <= tp)

        if sl_hit_this_bar and not hit_sl:
            hit_sl = True
            t_sl = (bar["datetime"] - ts).total_seconds() / 60.0
            break  # SL first (conservative)
        if tp_hit_this_bar and not hit_tp:
            hit_tp = True
            t_tp = (bar["datetime"] - ts).total_seconds() / 60.0
            break

    return {
        "valid": True,
        "peak_R": round(float(peak_R), 4),
        "mae_R": round(float(mae_R), 4),
        "hit_tp": hit_tp,
        "hit_sl": hit_sl,
        "hit_half_R": hit_half,
        "hit_one_R": hit_one,
        "time_to_tp_min": round(float(t_tp), 1) if t_tp is not None else None,
        "time_to_sl_min": round(float(t_sl), 1) if t_sl is not None else None,
    }


def percentile(s: pd.Series, q: float) -> float:
    if len(s) == 0:
        return float("nan")
    return round(float(np.percentile(s, q)), 4)


def summarize(df: pd.DataFrame, label: str) -> dict:
    if len(df) == 0:
        return {"label": label, "n": 0}
    return {
        "label": label,
        "n": int(len(df)),
        "peak_R_p50": percentile(df["peak_R"], 50),
        "peak_R_p60": percentile(df["peak_R"], 60),
        "peak_R_p80": percentile(df["peak_R"], 80),
        "mae_R_p20": percentile(df["mae_R"], 20),
        "mae_R_p50": percentile(df["mae_R"], 50),
        "hit_tp_pct": round(float(df["hit_tp"].mean()) * 100, 1),
        "hit_sl_pct": round(float(df["hit_sl"].mean()) * 100, 1),
        "hit_half_R_pct": round(float(df["hit_half_R"].mean()) * 100, 1),
        "hit_one_R_pct": round(float(df["hit_one_R"].mean()) * 100, 1),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audit", required=True, help="Path to ec_audit_*.jsonl")
    ap.add_argument("--horizon-min", type=int, default=300)
    ap.add_argument("--out-json", default=None)
    ap.add_argument("--out-md", default=None)
    args = ap.parse_args()

    audit_path = Path(args.audit)
    if not audit_path.is_absolute():
        audit_path = REPO_ROOT / audit_path

    df = load_ec_audit(audit_path)
    if len(df) == 0:
        print("No records in ec_audit file.")
        return 1

    print(f"Loaded {len(df)} ec_audit records")
    print(f"Events: {df['event'].value_counts().to_dict()}")
    print(f"Playbooks: {df['playbook'].value_counts().to_dict()}")

    symbols = df["symbol"].dropna().unique().tolist()
    bars_by_sym: dict[str, pd.DataFrame] = {}
    for sym in symbols:
        bars_by_sym[sym] = load_bars(sym)
        print(f"  {sym}: {len(bars_by_sym[sym])} 1m bars")

    # Replay each row
    results = []
    for i, row in df.iterrows():
        sym = row["symbol"]
        if sym not in bars_by_sym:
            continue
        r = replay_one(
            entry=float(row["entry"]),
            sl=float(row["sl"]),
            tp=float(row["tp1"]),
            direction=str(row["direction"]),
            ts=row["ts"],
            bars=bars_by_sym[sym],
            horizon_min=args.horizon_min,
        )
        if not r.get("valid"):
            continue
        out = {
            "playbook": row["playbook"],
            "event": row["event"],
            "direction": row["direction"],
            "symbol": sym,
            **r,
        }
        results.append(out)

    rdf = pd.DataFrame(results)
    print(f"\nReplayed {len(rdf)} valid setups")

    # Aggregate
    summary = {
        "n_total": int(len(rdf)),
        "horizon_min": args.horizon_min,
        "by_event": {},
        "by_event_playbook": {},
    }

    for ev in rdf["event"].unique():
        sub = rdf[rdf["event"] == ev]
        summary["by_event"][ev] = summarize(sub, ev)

    for (pb, ev), sub in rdf.groupby(["playbook", "event"]):
        summary["by_event_playbook"].setdefault(pb, {})[ev] = summarize(sub, ev)

    # Write outputs
    out_json = args.out_json or audit_path.parent / f"replay_{audit_path.stem}.json"
    out_md = args.out_md or audit_path.parent / f"replay_{audit_path.stem}.md"
    out_json = Path(out_json)
    out_md = Path(out_md)

    out_json.write_text(json.dumps(summary, indent=2, default=str))
    print(f"JSON: {out_json}")

    # MD
    md = [
        "# EC audit replay",
        "",
        f"- Source: `{audit_path.name}`",
        f"- Records replayed: **{len(rdf)}** / {len(df)} (invalid = bars missing or horizon empty)",
        f"- Horizon: {args.horizon_min} min (1m bars)",
        "",
        "## Summary by event (global)",
        "",
        "| Event | n | peak_R p50 | peak_R p80 | mae_R p20 | hit_TP % | hit_SL % | hit_0.5R % | hit_1R % |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for ev, s in summary["by_event"].items():
        md.append(
            f"| {ev} | {s['n']} | {s['peak_R_p50']:+.3f} | {s['peak_R_p80']:+.3f} "
            f"| {s['mae_R_p20']:+.3f} | {s['hit_tp_pct']} | {s['hit_sl_pct']} "
            f"| {s['hit_half_R_pct']} | {s['hit_one_R_pct']} |"
        )

    md.extend([
        "",
        "## Per playbook",
        "",
    ])
    for pb, by_ev in summary["by_event_playbook"].items():
        md.append(f"### {pb}")
        md.append("")
        md.append("| Event | n | peak_R p50 | peak_R p80 | mae_R p20 | hit_TP % | hit_SL % | hit_0.5R % | hit_1R % |")
        md.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
        for ev, s in by_ev.items():
            md.append(
                f"| {ev} | {s['n']} | {s['peak_R_p50']:+.3f} | {s['peak_R_p80']:+.3f} "
                f"| {s['mae_R_p20']:+.3f} | {s['hit_tp_pct']} | {s['hit_sl_pct']} "
                f"| {s['hit_half_R_pct']} | {s['hit_one_R_pct']} |"
            )
        md.append("")

    md.extend([
        "## Lecture",
        "",
        "- Comparer `rejected_no_commit` vs `passed` sur peak_R / hit_TP.",
        "- Si rejected peak_R ≥ passed → gate **destructeur** (éjecte des setups meilleurs ou égaux).",
        "- Si rejected peak_R < passed → gate **protecteur** (éjecte des setups pires).",
        "- Note intrabar : ce replay applique SL-avant-TP sur même bar (conservateur). Même convention que l'engine.",
        "- Horizon limité à 300min par défaut — raisonnable pour 5m playbooks mais peut tronquer winners très lents.",
        "",
    ])
    out_md.write_text("\n".join(md))
    print(f"MD: {out_md}")

    # Print summary to stdout
    print()
    for ev, s in summary["by_event"].items():
        print(f"{ev}: n={s['n']}, peak_R p80={s['peak_R_p80']:+.3f}, hit_TP={s['hit_tp_pct']}%")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
