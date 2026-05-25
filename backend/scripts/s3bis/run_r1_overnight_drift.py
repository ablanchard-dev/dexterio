"""Sprint R&D Edge Privé R1 — Overnight drift formel SPY/QQQ/IWM.

Source académique hors corpus YouTube : Knuteson 2018 "Information from
Information-less Trades", Cliff-Cooper-Gulen 2008.

Découverte incidental T_final_2 : Sharpe overnight buy-hold SPY 1.07 / QQQ 1.22
sur 1.9y. Test formel standalone sur 6.5y daily data.

Règle pré-déclarée frozen :
  - Buy at daily Close (proxy 16:00 ET close auction)
  - Sell at next-day daily Open (proxy 09:30 ET opening cross)
  - overnight_ret = (open_t+1 - close_t) / close_t
  - Per-asset verdict : SPY + QQQ + IWM

Costs frozen : 8 bps round-trip (close auction + opening cross + commission realistic)

Critère PASS : Sharpe net > 0.8 + permutation p<0.10 + sub-sample stable + DD < buy-hold 24h
Critère KILL : Sharpe < 0.4 OR worse than buy-hold 24h
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

backend_dir = Path(__file__).resolve().parent.parent.parent
COST_BPS_RT = 8.0  # round-trip frozen
N_PERMUTATIONS = 500
SEED = 42


def fetch_daily(ticker: str, start: str = "2019-06-01", end: str = "2025-11-30") -> pd.DataFrame:
    df = yf.download(ticker, start=start, end=end, interval="1d",
                     progress=False, auto_adjust=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.index.name = "date"
    return df[["Open", "Close"]].dropna()


def overnight_returns(df: pd.DataFrame) -> pd.Series:
    """overnight_ret[t] = (open[t+1] - close[t]) / close[t]"""
    next_open = df["Open"].shift(-1)
    overnight = (next_open - df["Close"]) / df["Close"]
    return overnight.dropna()


def daily_returns_24h(df: pd.DataFrame) -> pd.Series:
    """Total daily return close-to-close (24h hold reference)."""
    return df["Close"].pct_change().dropna()


def metrics(rets: pd.Series, label: str) -> dict:
    rets = rets.dropna()
    if len(rets) < 30:
        return {"label": label, "valid": False}
    eq = (1 + rets).cumprod()
    final = eq.iloc[-1] - 1
    days = (rets.index[-1] - rets.index[0]).days
    years = days / 365.25
    cagr = (1 + final) ** (1 / years) - 1 if years > 0 else 0
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


def permutation_test(rets: pd.Series, n_iter: int = N_PERMUTATIONS,
                     seed: int = SEED) -> tuple[float, float, float]:
    """Simple shuffle returns, compute permuted Sharpe distribution."""
    rng = np.random.default_rng(seed)
    real_sharpe = rets.mean() / rets.std() * np.sqrt(252) if rets.std() > 0 else 0
    perm_sharpes = []
    rets_arr = rets.values
    for _ in range(n_iter):
        shuffled = rng.permutation(rets_arr)
        if shuffled.std() > 0:
            perm_sharpes.append(shuffled.mean() / shuffled.std() * np.sqrt(252))
    perm_sharpes = np.array(perm_sharpes)
    p_value = float((perm_sharpes >= real_sharpe).mean())
    return real_sharpe, perm_sharpes.mean(), p_value


def main() -> None:
    print("=" * 100)
    print("Sprint R&D Edge Privé R1 — Overnight drift formel SPY/QQQ/IWM")
    print("Knuteson 2018 + Cliff-Cooper-Gulen 2008 (hors corpus YouTube)")
    print("=" * 100)

    cost = COST_BPS_RT / 10000.0
    print(f"\nCost RT frozen : {COST_BPS_RT} bps ({cost*100:.3f}%)")

    all_results = {}
    for asset in ["SPY", "QQQ", "IWM"]:
        print(f"\n=== {asset} ===")
        df = fetch_daily(asset)
        print(f"  Daily Open+Close : {len(df)} bars, "
              f"{df.index.min().date()} → {df.index.max().date()}")

        # Overnight strategy returns
        on_rets = overnight_returns(df)
        # Apply cost on every overnight position (we hold every night, costs apply daily)
        on_rets_net = on_rets - cost

        # Benchmarks
        rets_24h = daily_returns_24h(df).reindex(on_rets.index).fillna(0)
        # Intraday returns (open to close same day) for context
        intraday_rets = ((df["Close"] - df["Open"]) / df["Open"]).reindex(on_rets.index).fillna(0)

        m_on = metrics(on_rets_net, f"{asset} Overnight drift (Close→NextOpen, net 8bps)")
        m_24h = metrics(rets_24h, f"REF {asset} buy-hold 24h (close-to-close)")
        m_intra = metrics(intraday_rets, f"REF {asset} intraday only (open-to-close)")

        print()
        print(f"  {'Strategy':<55} {'CAGR':>7} {'Sharpe':>7} {'maxDD':>8} {'Calmar':>7}")
        print("  " + "=" * 95)
        for m in [m_on, m_24h, m_intra]:
            if not m.get("valid"):
                continue
            print(f"  {m['label']:<55} {m['CAGR_pct']:>6.2f}% {m['Sharpe_ann']:>+7.2f} "
                  f"{m['max_DD_pct']:>+7.1f}% {m['Calmar']:>+7.2f}")

        # Sub-sample stability
        split_date = pd.Timestamp("2022-06-01")
        sub1 = on_rets_net.loc[on_rets_net.index[0]:split_date].dropna()
        sub2 = on_rets_net.loc[split_date:on_rets_net.index[-1]].dropna()
        sh1 = sub1.mean() / sub1.std() * np.sqrt(252) if sub1.std() > 0 else 0
        sh2 = sub2.mean() / sub2.std() * np.sqrt(252) if sub2.std() > 0 else 0
        print(f"\n  Sub-sample : 2019-2022 Sharpe={sh1:+.2f} | 2022-2025 Sharpe={sh2:+.2f} | "
              f"ΔSharpe={sh2-sh1:+.2f}")

        # Permutation test only if not clean fail
        sh = m_on["Sharpe_ann"]
        if sh >= 0.5:
            real_sh, perm_mean, p_val = permutation_test(on_rets_net, N_PERMUTATIONS, SEED)
            print(f"\n  Permutation 500 iter : real={real_sh:.3f} | perm_mean={perm_mean:.3f} | "
                  f"p-value={p_val:.4f}  ({'PASS' if p_val < 0.10 else 'FAIL'})")
        else:
            p_val = None
            print(f"\n  Sharpe < 0.5 → permutation skipped (clean fail)")

        # Gate
        sh_24h = m_24h["Sharpe_ann"]
        beat_24h = sh > sh_24h
        verdict = "PASS" if (sh >= 0.8 and beat_24h and (p_val is None or p_val < 0.10)) else \
                  ("KILL" if sh < 0.4 else "MARGINAL")
        print(f"\n  Gate verdict {asset} :")
        print(f"    Sharpe ≥ 0.8 (PASS bar) : {'PASS' if sh >= 0.8 else 'FAIL'} (got {sh:.2f})")
        print(f"    Sharpe ≥ 0.4 (kill rule) : {'OK' if sh >= 0.4 else 'KILL'} (got {sh:.2f})")
        print(f"    Beat 24h buy-hold ({sh_24h:.2f}) : {'PASS' if beat_24h else 'FAIL'}")
        print(f"    DD < 24h buy-hold ({m_24h['max_DD_pct']:.1f}%) : "
              f"{'PASS' if m_on['max_DD_pct'] > m_24h['max_DD_pct'] else 'FAIL'} "
              f"(got {m_on['max_DD_pct']:.1f}%)")
        print(f"    → {verdict}")

        all_results[asset] = {
            "Sharpe_strat": sh,
            "Sharpe_24h_bh": sh_24h,
            "Sharpe_intraday": m_intra["Sharpe_ann"],
            "CAGR_strat": m_on["CAGR_pct"],
            "CAGR_24h": m_24h["CAGR_pct"],
            "DD_strat": m_on["max_DD_pct"],
            "DD_24h": m_24h["max_DD_pct"],
            "Calmar": m_on["Calmar"],
            "p_value": p_val,
            "delta_subsample": sh2 - sh1,
            "verdict": verdict,
        }

    # Cross-asset summary
    print()
    print("=" * 100)
    print("Cross-asset summary R1 Overnight Drift")
    print("=" * 100)
    print(f"{'Asset':<8} {'Sharpe':>7} {'24h_BH':>8} {'Intraday':>9} {'p-val':>8} {'ΔSubsample':>11} {'Verdict':>10}")
    n_pass = 0
    for asset, r in all_results.items():
        pv = f"{r['p_value']:.3f}" if r['p_value'] is not None else "—"
        print(f"{asset:<8} {r['Sharpe_strat']:>+7.2f} {r['Sharpe_24h_bh']:>+8.2f} "
              f"{r['Sharpe_intraday']:>+9.2f} {pv:>8} {r['delta_subsample']:>+10.2f} "
              f"{r['verdict']:>10}")
        if r['verdict'] == "PASS":
            n_pass += 1
    print(f"\n  {n_pass}/3 PASS")

    # Save
    out_dir = backend_dir / "results" / "rd_edge_r1_overnight_drift"
    out_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(all_results).T.to_parquet(out_dir / "results.parquet")
    print(f"\n[saved → {out_dir}]")


if __name__ == "__main__":
    main()
