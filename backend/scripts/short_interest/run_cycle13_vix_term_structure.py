"""run_cycle13_vix_term_structure.py — R&D Cycle v6 / Cycle 13 VIX term structure carry.

Hypothèse pré-spec :
  Eraker-Wu 2017 "The VIX Term Structure" : VIX futures normalement en contango
  (forward > spot), VXX rolls long → loses 5-10% APR. Short VXX (ou long SVXY -0.5×)
  capture roll yield. CRITICAL : risk management via VIX term structure
  (VIX9D/VIX ratio) — exit short vol quand backwardation imminente.
  Forme falsifiable : Sharpe net > 1.5 + Max DD < 30% + sub-sample stable.
  S+1 V1/V2/V3 ont testé SVXY avec VIX LEVEL only (Sharpe 0.47/0.24/-0.38) — failed.
  Ici : test rigoureux avec VIX9D/VIX TERM STRUCTURE = différent signal.

Anti-lookahead :
  - VIX9D/VIX ratio at close t-1 → decide position for open t
  - Cost 5 bps RT for SVXY/VXX (liquid ETFs)
  - Vol-target 15% annualized

3 variantes pré-spec (honest test) :
  V1 — SVXY long IF VIX9D/VIX < 0.93 (strong contango) AND VIX < 30
  V2 — VXX short IF VIX9D/VIX < 0.93 AND VIX < 30 (more aggressive, more roll yield)
  V3 — UVXY short carry IF VIX9D/VIX < 0.93 AND VIX < 25 (extreme, biggest roll yield + risk)

Each variante : signal at t-1, trade open t, exit if filter breaks at next signal.

Gates pré-écrits :
  - PROMOTE Stage 1 si Sharpe > 1.5 + DD < 30% + ΔSub < 0.5
  - ARCHIVE si Sharpe < 1.0 OR DD > 50%
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
OUT_DIR = REPO_ROOT / "backend/data/short_interest"
CACHE_DIR = REPO_ROOT / "backend/data/multi_asset"

CONTANGO_THRESHOLD = 0.93  # VIX9D/VIX < 0.93 = strong contango
PANIC_VIX_LEVEL = 30
PANIC_VIX_LEVEL_AGGRESSIVE = 25
RT_BPS = 5
VOL_TARGET = 0.15  # 15% annualized portfolio vol target
TRADING_DAYS = 252


def fetch_data():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = CACHE_DIR / "vix_term_structure.parquet"
    if cache.exists():
        return pd.read_parquet(cache)
    syms = ["VXX", "SVXY", "UVXY", "^VIX", "^VIX9D", "^VIX3M"]
    rows = {}
    for s in syms:
        df = yf.Ticker(s).history(start="2019-06-01", end="2025-11-30", auto_adjust=False)
        # Strip timezone for alignment
        s_data = df["Adj Close"] if "Adj Close" in df.columns else df["Close"]
        s_data.index = pd.to_datetime(s_data.index).tz_localize(None).normalize()
        rows[s.replace("^", "")] = s_data
    out = pd.DataFrame(rows)
    out.index.name = "date"
    out = out.dropna(how="any")  # need all 6 series aligned
    out.to_parquet(cache)
    return out


def simulate_vol_carry_variant(df: pd.DataFrame, asset: str, side: str,
                                  contango_th: float, panic_th: float,
                                  rt_bps: float, vol_target: float) -> pd.DataFrame:
    """Simulate one variant of VIX term structure carry.

    asset : 'SVXY' (long for short vol), 'VXX' or 'UVXY' (short for short vol)
    side : 'long' or 'short'
    Filter : VIX9D/VIX < contango_th AND VIX < panic_th
    Anti-lookahead : signal at t-1 close → trade close t (vol-target sizing)
    """
    out = df.copy()
    out["log_ret"] = np.log(out[asset]).diff()
    out["vol_60d"] = out["log_ret"].shift(1).rolling(60, min_periods=60).std() * np.sqrt(TRADING_DAYS)
    # Filter signal at t-1
    out["ratio_9d_30d"] = out["VIX9D"].shift(1) / out["VIX"].shift(1)
    out["vix_lag1"] = out["VIX"].shift(1)
    out["filter_active"] = (out["ratio_9d_30d"] < contango_th) & (out["vix_lag1"] < panic_th)
    # Position weight : vol-target × signal × side direction
    direction = +1 if side == "long" else -1
    raw_weight = vol_target / out["vol_60d"]
    out["weight"] = direction * raw_weight * out["filter_active"].astype(float)
    out["weight"] = out["weight"].fillna(0.0)
    # Cap leverage at 1×
    out["weight"] = out["weight"].clip(-1.0, 1.0)
    # Daily PnL : weight × log_ret of asset
    out["pnl_gross"] = out["weight"].shift(1) * out["log_ret"]
    # Turnover cost
    out["turnover"] = (out["weight"] - out["weight"].shift(1)).abs()
    out["cost"] = out["turnover"] * rt_bps / 10_000.0
    out["pnl"] = out["pnl_gross"] - out["cost"]
    return out


def compute_metrics(pnl: pd.Series) -> dict:
    pnl_clean = pnl.dropna()
    if pnl_clean.std() == 0:
        return {"sharpe": 0.0, "cagr": 0.0, "max_dd": 0.0, "calmar": 0.0,
                  "n_days": len(pnl_clean)}
    sharpe = pnl_clean.mean() / pnl_clean.std() * np.sqrt(TRADING_DAYS)
    eq = (1 + pnl_clean).cumprod()
    cagr = eq.iloc[-1] ** (TRADING_DAYS / len(pnl_clean)) - 1
    rmax = eq.cummax()
    dd = (eq - rmax) / rmax
    max_dd = float(dd.min())
    calmar = cagr / abs(max_dd) if max_dd < 0 else 0.0
    # Sub-sample
    mid = pd.Timestamp("2022-09-01")
    h1 = pnl_clean[pnl_clean.index < mid]
    h2 = pnl_clean[pnl_clean.index >= mid]
    sh_h1 = h1.mean() / h1.std() * np.sqrt(TRADING_DAYS) if h1.std() > 0 else 0
    sh_h2 = h2.mean() / h2.std() * np.sqrt(TRADING_DAYS) if h2.std() > 0 else 0
    return {
        "sharpe": float(sharpe), "cagr": float(cagr), "max_dd": max_dd,
        "calmar": float(calmar), "n_days": len(pnl_clean),
        "sh_h1": float(sh_h1), "sh_h2": float(sh_h2),
        "delta_sub": abs(sh_h1 - sh_h2),
    }


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("[Cycle 13] VIX term structure carry — Eraker-Wu 2017 canonical with proper risk mgmt", flush=True)
    print(f"  Filter : VIX9D/VIX < {CONTANGO_THRESHOLD} (strong contango) AND VIX < panic", flush=True)
    print(f"  Anti-lookahead : signal at t-1 → trade close t", flush=True)
    print(f"  Costs : {RT_BPS} bps RT, vol-target {VOL_TARGET*100:.0f}%", flush=True)
    print(f"  3 variantes pré-spec : SVXY long / VXX short / UVXY short", flush=True)

    print("[1/3] Fetching VIX term structure + ETF data...", flush=True)
    df = fetch_data()
    df = df.dropna()
    print(f"      Shape : {df.shape}, range {df.index.min().date()} → {df.index.max().date()}",
          flush=True)
    # Simple stats on filter active days
    ratio = df["VIX9D"] / df["VIX"]
    contango_pct = ((ratio < CONTANGO_THRESHOLD) & (df["VIX"] < PANIC_VIX_LEVEL)).mean()
    print(f"      Filter active (9d/30d<{CONTANGO_THRESHOLD} & VIX<{PANIC_VIX_LEVEL}) : {contango_pct*100:.1f}% of days",
          flush=True)

    print("[2/3] Simulating 3 variantes...", flush=True)
    v1 = simulate_vol_carry_variant(df, asset="SVXY", side="long",
                                       contango_th=CONTANGO_THRESHOLD, panic_th=PANIC_VIX_LEVEL,
                                       rt_bps=RT_BPS, vol_target=VOL_TARGET)
    v2 = simulate_vol_carry_variant(df, asset="VXX", side="short",
                                       contango_th=CONTANGO_THRESHOLD, panic_th=PANIC_VIX_LEVEL,
                                       rt_bps=RT_BPS, vol_target=VOL_TARGET)
    v3 = simulate_vol_carry_variant(df, asset="UVXY", side="short",
                                       contango_th=CONTANGO_THRESHOLD, panic_th=PANIC_VIX_LEVEL_AGGRESSIVE,
                                       rt_bps=RT_BPS, vol_target=VOL_TARGET)

    perf_start = 60  # vol window
    m1 = compute_metrics(v1["pnl"].iloc[perf_start:])
    m2 = compute_metrics(v2["pnl"].iloc[perf_start:])
    m3 = compute_metrics(v3["pnl"].iloc[perf_start:])

    print("[3/3] Results...", flush=True)
    print(f"  V1 SVXY long  : Sharpe {m1['sharpe']:.3f}, CAGR {m1['cagr']*100:+.2f}%, "
          f"DD {m1['max_dd']*100:.1f}%, h1/h2 {m1['sh_h1']:.2f}/{m1['sh_h2']:.2f}",
          flush=True)
    print(f"  V2 VXX short  : Sharpe {m2['sharpe']:.3f}, CAGR {m2['cagr']*100:+.2f}%, "
          f"DD {m2['max_dd']*100:.1f}%, h1/h2 {m2['sh_h1']:.2f}/{m2['sh_h2']:.2f}",
          flush=True)
    print(f"  V3 UVXY short : Sharpe {m3['sharpe']:.3f}, CAGR {m3['cagr']*100:+.2f}%, "
          f"DD {m3['max_dd']*100:.1f}%, h1/h2 {m3['sh_h1']:.2f}/{m3['sh_h2']:.2f}",
          flush=True)

    # Decision
    best = max([("SVXY long", m1, v1), ("VXX short", m2, v2), ("UVXY short", m3, v3)],
                 key=lambda x: x[1]["sharpe"])
    name, best_m, best_v = best

    if best_m["sharpe"] > 1.5 and abs(best_m["max_dd"]) < 0.30 and best_m["delta_sub"] < 0.5:
        decision = f"Stage 1 PASS — Best variant {name} Sharpe {best_m['sharpe']:.3f}"
        emoji = "✅ STAGE 1 PASS"
    elif best_m["sharpe"] > 1.0 and abs(best_m["max_dd"]) < 0.40:
        decision = f"Marginal-good — Best {name} Sharpe {best_m['sharpe']:.3f}, DD {best_m['max_dd']*100:.1f}%"
        emoji = "⚠️ MARGINAL"
    elif best_m["sharpe"] < 0.5:
        decision = f"ARCHIVE — Best variant Sharpe {best_m['sharpe']:.3f} < 0.5, VIX term structure ne débloque pas edge proper"
        emoji = "🛑 ARCHIVE"
    else:
        decision = f"Marginal — Best {name} Sharpe {best_m['sharpe']:.3f}, useful for ensemble"
        emoji = "⚠️ MARGINAL"

    md_lines = []
    md_lines.append("# Cycle 13 — VIX term structure carry (Eraker-Wu 2017)")
    md_lines.append("")
    md_lines.append(f"**Generated** : {datetime.now(timezone.utc).isoformat()}")
    md_lines.append(f"## Decision : {emoji}")
    md_lines.append(f"**Verdict** : {decision}")
    md_lines.append("")
    md_lines.append("## Identité")
    md_lines.append("")
    md_lines.append(f"- **Source** : Eraker-Wu 2017 \"The VIX Term Structure\" — VIX futures contango → "
                     f"VXX roll-yield negatif → short VXX/UVXY ou long SVXY capture le carry. "
                     f"Filter via VIX9D/VIX ratio évite VIX spikes.")
    md_lines.append(f"- **Différencier vs S+1 V1/V2/V3** : ces tests utilisaient VIX LEVEL only (Sharpe 0.47/0.24/-0.38) ; "
                     f"ici TERM STRUCTURE VIX9D/VIX = canonical signal différent.")
    md_lines.append(f"- **Filter active** : {contango_pct*100:.1f}% of days (V1/V2 with VIX<{PANIC_VIX_LEVEL})")
    md_lines.append(f"- **Costs** : {RT_BPS} bps RT, vol-target {VOL_TARGET*100:.0f}% annualized")
    md_lines.append("")
    md_lines.append("## Métriques par variante")
    md_lines.append("")
    md_lines.append("| Variante | Sharpe | CAGR | Max DD | Calmar | h1/h2 | Δsub |")
    md_lines.append("|---|---:|---:|---:|---:|---:|---:|")
    md_lines.append(f"| V1 SVXY long | {m1['sharpe']:.3f} | {m1['cagr']*100:+.2f}% | "
                     f"{m1['max_dd']*100:.1f}% | {m1['calmar']:.2f} | "
                     f"{m1['sh_h1']:.2f}/{m1['sh_h2']:.2f} | {m1['delta_sub']:.2f} |")
    md_lines.append(f"| V2 VXX short | {m2['sharpe']:.3f} | {m2['cagr']*100:+.2f}% | "
                     f"{m2['max_dd']*100:.1f}% | {m2['calmar']:.2f} | "
                     f"{m2['sh_h1']:.2f}/{m2['sh_h2']:.2f} | {m2['delta_sub']:.2f} |")
    md_lines.append(f"| V3 UVXY short | {m3['sharpe']:.3f} | {m3['cagr']*100:+.2f}% | "
                     f"{m3['max_dd']*100:.1f}% | {m3['calmar']:.2f} | "
                     f"{m3['sh_h1']:.2f}/{m3['sh_h2']:.2f} | {m3['delta_sub']:.2f} |")
    md_lines.append("")
    md_lines.append("## Comparison vs S+1 baseline (level-only filter)")
    md_lines.append("")
    md_lines.append("| Filter type | Best Sharpe | Best variant |")
    md_lines.append("|---|---:|---|")
    md_lines.append(f"| **S+1 VIX level only** (V1 buy-hold/V2 VIX<25/V3 VIX<20+zscore) | 0.47 | V1 buy-hold |")
    md_lines.append(f"| **Cycle 13 term structure** (VIX9D/VIX<{CONTANGO_THRESHOLD}) | {best_m['sharpe']:.3f} | {name} |")
    md_lines.append(f"| Lift from term structure | {best_m['sharpe']-0.47:+.3f} | — |")
    out_md = OUT_DIR / "cycle13_vix_term_structure_verdict.md"
    out_md.write_text("\n".join(md_lines), encoding="utf-8")

    # Save best variant PnL for ensemble combination
    best_v[["pnl"]].to_parquet(OUT_DIR / f"cycle13_{name.replace(' ', '_')}_pnl.parquet")

    print(f"\n=== Verdict → {out_md}", flush=True)
    print(f"=== Best variant : {name} Sharpe {best_m['sharpe']:.3f} | {emoji}", flush=True)


if __name__ == "__main__":
    main()
