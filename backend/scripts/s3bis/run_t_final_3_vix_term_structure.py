"""Sprint Ultra-Final T_final_3 — VIX term structure timing signal.

Source académique : Eraker-Wu 2017 — différent de SVXY VRP retail (level vol)
qu'on a testé en S+1. Ici on utilise le TERM STRUCTURE comme timing signal.

Data gate PASS : ^VIX + ^VIX9D + ^VIX3M tous disponibles 6.5y yfinance free.

Règle pré-déclarée frozen (1 seule, pas 15 ratios) :
  - Signal : VIX / VIX3M ratio (front vs back month, contango/backwardation)
  - Long SVXY (= short front vol via -0.5x ETF) when ratio < 0.95 (steep contango = safe to short vol)
  - Cash when ratio >= 0.95
  - Daily check, no intraday switch
  - 5 bps cost per signal change

Benchmarks : SPY buy-hold + SVXY buy-hold + cash.

Critère PASS : Sharpe net > 0.7 + DD inférieur SVXY buy-hold + sub-sample stable
Critère KILL : Sharpe < 0.4 OR worse than SVXY buy-hold
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

backend_dir = Path(__file__).resolve().parent.parent.parent
DATA_F2 = backend_dir / "data" / "f2_daily"
DATA_VIX_VRP = backend_dir / "data" / "vix_vrp"

START = "2019-06-01"
END = "2025-11-30"
RATIO_THRESHOLD = 0.95  # frozen pre-declared, no tuning
COST_BPS = 5.0


def fetch_vix_term() -> pd.DataFrame:
    """Fetch ^VIX, ^VIX9D, ^VIX3M aligned daily."""
    out = {}
    for ticker, label in [("^VIX", "VIX"), ("^VIX9D", "VIX9D"), ("^VIX3M", "VIX3M")]:
        df = yf.download(ticker, start=START, end=END, interval="1d",
                         progress=False, auto_adjust=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        out[label] = df["Close"]
    df = pd.concat(out, axis=1).dropna()
    df.index.name = "date"
    return df


def load_svxy() -> pd.Series:
    df = pd.read_parquet(DATA_VIX_VRP / "SVXY_1d.parquet")
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")["Close"].sort_index()


def load_spy() -> pd.Series:
    df = pd.read_parquet(DATA_F2 / "SPY_1d.parquet")
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")["Close"].sort_index()


def metrics(rets: pd.Series, label: str) -> dict:
    rets = rets.dropna()
    if len(rets) < 30:
        return {"label": label, "valid": False}
    eq = (1 + rets).cumprod()
    final_ret = eq.iloc[-1] - 1
    days = (rets.index[-1] - rets.index[0]).days
    years = days / 365.25
    cagr = (1 + final_ret) ** (1 / years) - 1 if years > 0 else 0
    sharpe = rets.mean() / rets.std() * np.sqrt(252) if rets.std() > 0 else 0
    rm = eq.expanding().max()
    dd = float((eq / rm - 1).min())
    calmar = cagr / abs(dd) if dd < 0 else 0
    return {
        "label": label, "valid": True, "n_days": len(rets),
        "CAGR_pct": cagr * 100, "Sharpe_ann": float(sharpe),
        "max_DD_pct": dd * 100, "Calmar": calmar,
        "vol_ann_pct": rets.std() * np.sqrt(252) * 100,
    }


def main() -> None:
    print("=" * 100)
    print("Sprint Ultra-Final T_final_3 — VIX term structure timing (Eraker-Wu 2017)")
    print("=" * 100)

    print("\nFetching VIX term structure...")
    vix_term = fetch_vix_term()
    vix_term["vix_vix3m_ratio"] = vix_term["VIX"] / vix_term["VIX3M"]
    print(f"  Loaded {len(vix_term)} days, {vix_term.index.min().date()} → {vix_term.index.max().date()}")
    print(f"  VIX/VIX3M ratio : mean={vix_term['vix_vix3m_ratio'].mean():.3f}, "
          f"p10={vix_term['vix_vix3m_ratio'].quantile(0.1):.3f}, "
          f"p90={vix_term['vix_vix3m_ratio'].quantile(0.9):.3f}")
    print(f"  % time ratio < {RATIO_THRESHOLD} (steep contango) : "
          f"{(vix_term['vix_vix3m_ratio'] < RATIO_THRESHOLD).mean()*100:.1f}%")

    # Signal pre-declared frozen : long SVXY when VIX/VIX3M < 0.95
    # Use prior day's ratio (no lookahead)
    signal = (vix_term["vix_vix3m_ratio"].shift(1) < RATIO_THRESHOLD).astype(float)

    # Load SVXY prices
    svxy = load_svxy()
    common = vix_term.index.intersection(svxy.index)
    signal = signal.loc[common]
    svxy_aligned = svxy.loc[common]
    svxy_rets = svxy_aligned.pct_change().fillna(0)

    # Strategy : long SVXY when signal=1, cash otherwise
    pos = signal.shift(1).fillna(0)  # use yesterday's signal for today's return
    daily_strat = pos * svxy_rets
    pos_change = signal.diff().abs().fillna(0)
    cost = pos_change * (COST_BPS / 10000.0)
    daily_strat_net = daily_strat - cost

    # Benchmarks
    spy = load_spy().loc[common]
    spy_rets = spy.pct_change().fillna(0)
    svxy_bh_rets = svxy_rets.copy()

    m_strat = metrics(daily_strat_net, "T_final_3 VIX term structure (long SVXY if VIX/VIX3M<0.95)")
    m_svxy = metrics(svxy_bh_rets, "REF SVXY buy-hold")
    m_spy = metrics(spy_rets, "REF SPY buy-hold")

    n_signal_days = int(pos.sum())
    n_total = len(pos)
    pct_active = float(n_signal_days / n_total * 100) if n_total > 0 else 0
    n_trades = int((signal.diff().abs() > 0).sum() / 2)
    print(f"\n  Position : {n_signal_days}/{n_total} days active ({pct_active:.1f}%), "
          f"~{n_trades} round-trip trades")

    print()
    print(f"{'Strategy':<60} {'CAGR':>7} {'Sharpe':>7} {'maxDD':>8} {'Calmar':>7} {'vol':>6}")
    print("=" * 100)
    for m in [m_strat, m_svxy, m_spy]:
        if not m.get("valid"):
            continue
        print(f"{m['label']:<60} {m['CAGR_pct']:>6.2f}% {m['Sharpe_ann']:>+7.2f} "
              f"{m['max_DD_pct']:>+7.1f}% {m['Calmar']:>+7.2f} "
              f"{m['vol_ann_pct']:>5.1f}%")

    # Sub-sample
    split_date = pd.Timestamp("2022-06-01")
    print()
    print("Sub-sample 2019-2022 vs 2022-2025 :")
    for label, rets in [("T3 VIX term structure", daily_strat_net),
                         ("SVXY buy-hold", svxy_bh_rets),
                         ("SPY buy-hold", spy_rets)]:
        sub1 = rets.loc[rets.index[0]:split_date].dropna()
        sub2 = rets.loc[split_date:rets.index[-1]].dropna()
        sh1 = sub1.mean() / sub1.std() * np.sqrt(252) if sub1.std() > 0 else 0
        sh2 = sub2.mean() / sub2.std() * np.sqrt(252) if sub2.std() > 0 else 0
        print(f"  {label:<35} 2019-2022 Sharpe={sh1:+.2f} | 2022-2025 Sharpe={sh2:+.2f} | "
              f"ΔSharpe={sh2-sh1:+.2f}")

    # Gate
    print()
    print("=" * 100)
    print("Gate plan T_final_3")
    print("=" * 100)
    sh = m_strat["Sharpe_ann"]
    sh_svxy = m_svxy["Sharpe_ann"]
    sh_spy = m_spy["Sharpe_ann"]
    cal = m_strat["Calmar"]
    cal_svxy = m_svxy["Calmar"]
    print(f"  Sharpe ≥ 0.7 (PASS bar) : {'PASS' if sh >= 0.7 else 'FAIL'} (got {sh:.2f})")
    print(f"  Sharpe ≥ 0.4 (kill rule) : {'OK' if sh >= 0.4 else 'KILL'} (got {sh:.2f})")
    print(f"  Beat SVXY buy-hold ({sh_svxy:.2f}) : {'PASS' if sh > sh_svxy else 'FAIL'}")
    print(f"  Beat SPY buy-hold ({sh_spy:.2f}) : {'PASS' if sh > sh_spy else 'FAIL'}")
    print(f"  DD inférieur SVXY buy-hold ({m_svxy['max_DD_pct']:.1f}%) : "
          f"{'PASS' if m_strat['max_DD_pct'] > m_svxy['max_DD_pct'] else 'FAIL'} "
          f"(got {m_strat['max_DD_pct']:.1f}%)")

    # Save
    out_dir = backend_dir / "results" / "ultra_final_t3_vix_term_structure"
    out_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({
        "vix_term_strat": (1 + daily_strat_net).cumprod(),
        "svxy_bh": (1 + svxy_bh_rets).cumprod(),
        "spy_bh": (1 + spy_rets).cumprod(),
        "vix_vix3m_ratio": vix_term["vix_vix3m_ratio"].loc[common],
    }).to_parquet(out_dir / "equity_curves.parquet")
    print(f"\n[saved → {out_dir}]")


if __name__ == "__main__":
    main()
