"""Leg 4.2 — VIX-regime overlay sur cohort survivor_v1 (read-only post-hoc).

Dossier : backend/knowledge/overlays/leg42_vix_regime_v1/dossier.md
Plan    : §0.5 arbre Leg 4.2 — filtre régime VIX 15-25 (mean-rev fertile §0.4-bis).

Usage :
    cd backend && .venv/bin/python scripts/leg42_vix_overlay.py
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import yfinance as yf


SURVIVOR_PLAYBOOKS = [
    "News_Fade",
    "Engulfing_Bar_V056",
    "Session_Open_Scalp",
    "Liquidity_Sweep_Scalp",
]
CORPUS_WEEKS = ["jun_w3", "aug_w3", "oct_w2", "nov_w4"]
VIX_BAND_LOW = 15.0
VIX_BAND_HIGH = 25.0
REPO_ROOT = Path(__file__).resolve().parents[1]
SURVIVOR_DIR = REPO_ROOT / "results" / "labs" / "mini_week" / "survivor_v1"
OUT_DIR = REPO_ROOT / "results" / "labs" / "mini_week" / "leg42_vix_overlay_v1"


def load_cohort_trades() -> pd.DataFrame:
    frames = []
    for w in CORPUS_WEEKS:
        p = SURVIVOR_DIR / w / f"trades_miniweek_survivor_v1_{w}_AGGRESSIVE_DAILY_SCALP.parquet"
        df = pd.read_parquet(p)
        df["week_label"] = w
        frames.append(df)
    df = pd.concat(frames, ignore_index=True)
    df = df[df["playbook"].isin(SURVIVOR_PLAYBOOKS)].copy()
    df["trading_date"] = pd.to_datetime(df["timestamp_entry"]).dt.tz_convert("America/New_York").dt.date
    return df


def load_vix_daily(start: str = "2025-05-01", end: str = "2025-12-01") -> pd.DataFrame:
    vix = yf.Ticker("^VIX").history(start=start, end=end, interval="1d")
    vix = vix.reset_index()
    vix["Date"] = pd.to_datetime(vix["Date"]).dt.tz_localize(None).dt.date
    vix = vix[["Date", "Close"]].rename(columns={"Date": "vix_date", "Close": "vix_close"})
    vix = vix.sort_values("vix_date").reset_index(drop=True)
    return vix


def merge_prior_day_vix(trades: pd.DataFrame, vix: pd.DataFrame) -> pd.DataFrame:
    # Strict prior day — shift VIX by 1 trading day on the VIX timeline (not calendar).
    vix = vix.sort_values("vix_date").reset_index(drop=True).copy()
    vix["vix_close_prior"] = vix["vix_close"].shift(1)
    vix["vix_prior_date"] = vix["vix_date"].shift(1)
    vix = vix.dropna(subset=["vix_close_prior"])

    t = trades.sort_values("trading_date").copy()
    t["trading_date"] = pd.to_datetime(t["trading_date"])
    vix["vix_date"] = pd.to_datetime(vix["vix_date"])

    merged = pd.merge_asof(
        t,
        vix[["vix_date", "vix_close_prior", "vix_prior_date"]],
        left_on="trading_date",
        right_on="vix_date",
        direction="backward",
    )
    merged["vix_band"] = pd.cut(
        merged["vix_close_prior"],
        bins=[-float("inf"), VIX_BAND_LOW, VIX_BAND_HIGH, float("inf")],
        labels=["low", "fertile", "panic"],
        right=False,
    )
    return merged


def compute_metrics(df: pd.DataFrame) -> dict:
    if len(df) == 0:
        return {"n": 0, "WR": None, "E_R": None, "PF": None, "total_R": 0.0}
    r = df["r_multiple"].astype(float)
    wins = r > 0
    losses = r < 0
    pf = float(r[wins].sum() / -r[losses].sum()) if r[losses].sum() < 0 else float("inf")
    return {
        "n": int(len(df)),
        "WR": float(wins.mean()),
        "E_R": float(r.mean()),
        "PF": pf,
        "total_R": float(r.sum()),
        "peak_R_p80": float(df["peak_r"].astype(float).quantile(0.8)) if "peak_r" in df else None,
        "mae_R_p20": float(df["mae_r"].astype(float).quantile(0.2)) if "mae_r" in df else None,
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("[leg42] loading cohort trades ...")
    trades = load_cohort_trades()
    print(f"[leg42] cohort trades loaded : n={len(trades)} (4 survivors × 4 weeks)")

    print("[leg42] fetching VIX daily via yfinance ...")
    vix = load_vix_daily()
    print(f"[leg42] VIX daily rows : {len(vix)} (min={vix['vix_close'].min():.2f}, max={vix['vix_close'].max():.2f})")

    merged = merge_prior_day_vix(trades, vix)
    print(f"[leg42] merged n={len(merged)}  (VIX NaN={merged['vix_close_prior'].isna().sum()})")

    baseline = compute_metrics(merged)
    subset_fertile = merged[merged["vix_band"] == "fertile"]
    subset_low = merged[merged["vix_band"] == "low"]
    subset_panic = merged[merged["vix_band"] == "panic"]

    result = {
        "config": {
            "cohort_playbooks": SURVIVOR_PLAYBOOKS,
            "corpus_weeks": CORPUS_WEEKS,
            "vix_band_low": VIX_BAND_LOW,
            "vix_band_high": VIX_BAND_HIGH,
            "vix_source": "yfinance ^VIX daily close",
        },
        "baseline_cohort": baseline,
        "subset_fertile_15_25": compute_metrics(subset_fertile),
        "subset_low_lt_15": compute_metrics(subset_low),
        "subset_panic_ge_25": compute_metrics(subset_panic),
        "delta_fertile_vs_baseline": {
            "E_R": compute_metrics(subset_fertile)["E_R"] - baseline["E_R"] if baseline["E_R"] is not None else None,
            "n_share": compute_metrics(subset_fertile)["n"] / baseline["n"] if baseline["n"] > 0 else None,
        },
        "per_playbook_fertile": {},
        "per_playbook_baseline": {},
    }
    for pb in SURVIVOR_PLAYBOOKS:
        sub_pb_fertile = subset_fertile[subset_fertile["playbook"] == pb]
        sub_pb_base = merged[merged["playbook"] == pb]
        result["per_playbook_fertile"][pb] = compute_metrics(sub_pb_fertile)
        result["per_playbook_baseline"][pb] = compute_metrics(sub_pb_base)

    band_shares = merged["vix_band"].value_counts(normalize=True).to_dict()
    result["band_shares"] = {str(k): float(v) for k, v in band_shares.items()}

    out_json = OUT_DIR / "leg42_vix_overlay_results.json"
    with out_json.open("w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"[leg42] wrote {out_json}")

    # Print executive summary
    print("\n=== EXECUTIVE SUMMARY ===")
    print(f"baseline cohort : n={baseline['n']} E[R]={baseline['E_R']:.4f} WR={baseline['WR']:.3f} PF={baseline['PF']:.3f}")
    sf = result["subset_fertile_15_25"]
    if sf["n"] > 0:
        print(f"subset VIX fertile [15,25] : n={sf['n']} E[R]={sf['E_R']:.4f} WR={sf['WR']:.3f} PF={sf['PF']:.3f}")
    sl = result["subset_low_lt_15"]
    if sl["n"] > 0:
        print(f"subset VIX low <15        : n={sl['n']} E[R]={sl['E_R']:.4f} WR={sl['WR']:.3f}")
    sp = result["subset_panic_ge_25"]
    if sp["n"] > 0:
        print(f"subset VIX panic >=25     : n={sp['n']} E[R]={sp['E_R']:.4f} WR={sp['WR']:.3f}")
    print(f"band shares : {result['band_shares']}")
    print("\nper-playbook baseline vs fertile :")
    for pb in SURVIVOR_PLAYBOOKS:
        b = result["per_playbook_baseline"][pb]
        f_ = result["per_playbook_fertile"][pb]
        if b["n"] > 0:
            print(f"  {pb:25s} baseline n={b['n']:3d} E[R]={b['E_R']:+.4f}  |  fertile n={f_['n']:3d} E[R]={f_['E_R']:+.4f}" if f_['E_R'] is not None else f"  {pb:25s} baseline n={b['n']:3d} E[R]={b['E_R']:+.4f}  |  fertile n=0")


if __name__ == "__main__":
    main()
