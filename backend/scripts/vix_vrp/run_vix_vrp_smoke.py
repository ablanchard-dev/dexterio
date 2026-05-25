"""S+1 J1.3 — VIX VRP smoke baseline (3 variantes pré-déclarées strictes).

Variantes (frozen, non-négociables) :
    V1 : SVXY buy-and-hold (raw VRP existence reference)
    V2 : SVXY long if VIX prior < 25 else cash (regime filter)
    V3 : SVXY long if (VIX prior < 20) AND (vxx_svxy_zscore_20d < 0) else cash

Métriques (niveau système + niveau exploitation) :
    - Sharpe net annualized (daily)
    - CAGR
    - Max DD
    - n_trades (entries)
    - capture_summary (median_capture_ratio, % weak/early/late/efficient, headline)
    - Sub-sample stability : 2019-2022 vs 2022-2025

Costs simulés :
    - 0.10% per round-trip per entry/exit (spread + commission ETF retail)

Usage : python backend/scripts/vix_vrp/run_vix_vrp_smoke.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

backend_dir = Path(__file__).resolve().parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from research.feature_store import build_vix_vrp_features
from research.label_factory import capture_summary

DATA_DIR = backend_dir / "data"
F2_DIR = DATA_DIR / "f2_daily"
VIX_VRP_DIR = DATA_DIR / "vix_vrp"

ENTRY_EXIT_COST_BPS = 10.0  # 0.10% round-trip per entry/exit (10 bps each side)


def load_data() -> tuple[pd.Series, pd.Series, pd.Series]:
    vix = pd.read_parquet(F2_DIR / "VIX_1d.parquet")
    vix["date"] = pd.to_datetime(vix["date"])
    vix = vix.set_index("date")["Close"].rename("VIX")

    vxx = pd.read_parquet(VIX_VRP_DIR / "VXX_1d.parquet")
    vxx["date"] = pd.to_datetime(vxx["date"])
    vxx = vxx.set_index("date")["Close"].rename("VXX")

    svxy = pd.read_parquet(VIX_VRP_DIR / "SVXY_1d.parquet")
    svxy["date"] = pd.to_datetime(svxy["date"])
    svxy = svxy.set_index("date")["Close"].rename("SVXY")

    common = vix.index.intersection(vxx.index).intersection(svxy.index)
    return vix.loc[common], vxx.loc[common], svxy.loc[common]


def compute_metrics(returns: pd.Series, position: pd.Series, label: str) -> dict:
    """Compute system + exploitation metrics for a strategy.

    Args:
        returns : daily strategy returns (after costs already applied)
        position : daily position 0 (cash) or 1 (long SVXY)
        label : variant name
    """
    eq = (1 + returns).cumprod()
    days = (eq.index[-1] - eq.index[0]).total_seconds() / 86400
    years = days / 365.0
    final_ret = eq.iloc[-1] - 1
    cagr = (1 + final_ret) ** (1 / years) - 1 if years > 0 else 0
    sharpe = float(returns.mean() / returns.std() * np.sqrt(252)) if returns.std() > 0 else 0
    rm = eq.expanding().max()
    dd = (eq / rm - 1).min()
    pct_in = position.mean() * 100
    return {
        "label": label,
        "n_days": len(returns),
        "pct_time_in_market": pct_in,
        "total_return_pct": final_ret * 100,
        "CAGR_pct": cagr * 100,
        "Sharpe_ann": sharpe,
        "max_DD_pct": dd * 100,
        "vol_ann_pct": returns.std() * np.sqrt(252) * 100,
        "equity": eq,
    }


def trades_from_position(returns_asset: pd.Series, position: pd.Series,
                          cost_bps: float = ENTRY_EXIT_COST_BPS) -> tuple[pd.Series, pd.DataFrame]:
    """Convert a position series (0/1 daily) into discrete trades + apply costs.

    Returns:
        (strategy_daily_returns, trades_df) where trades_df has r_multiple + peak_r.
    """
    pos_change = position.diff().fillna(0)
    entries = position.index[(position.shift(1).fillna(0) == 0) & (position == 1)]
    exits = position.index[(position.shift(1).fillna(0) == 1) & (position == 0)]
    # Daily strategy returns = position(t-1) * asset_ret(t) (entry at close prior, exit at close)
    strat_ret = position.shift(1).fillna(0) * returns_asset
    # Apply costs on entry+exit days
    cost_per_event = cost_bps / 10000.0
    cost_mask = (pos_change != 0).astype(float)
    strat_ret = strat_ret - cost_mask * cost_per_event

    # Build trades : pair each entry with next exit
    trades = []
    if position.iloc[0] == 1:
        # If position starts in market, virtual entry at index[0]
        entries = pd.Index([position.index[0]]).append(entries)
    if position.iloc[-1] == 1:
        # If still in market at end, virtual exit at last index
        exits = exits.append(pd.Index([position.index[-1]]))
    for ent, ext in zip(entries, exits):
        trade_ret = strat_ret.loc[ent:ext]
        if len(trade_ret) < 2:
            continue
        cum_eq = (1 + trade_ret).cumprod()
        # Compute "R" — using initial trade-day vol as risk unit (daily vol)
        # Simple approximation : R = total trade return in % terms / daily vol_target 1%
        # Since we don't have explicit SL, use 1% as risk unit (~ 1% adverse move expected)
        risk_unit = 0.01  # 1% = 1R approximation for a swing-style trade
        peak_excursion = cum_eq.max() - 1
        final_excursion = cum_eq.iloc[-1] - 1
        peak_r = peak_excursion / risk_unit
        realized_r = final_excursion / risk_unit
        trades.append({
            "entry": ent,
            "exit": ext,
            "duration_days": (ext - ent).days,
            "peak_r": float(peak_r),
            "r_multiple": float(realized_r),
            "trade_return_pct": float(final_excursion * 100),
        })
    return strat_ret, pd.DataFrame(trades)


def main() -> None:
    vix, vxx, svxy = load_data()
    print(f"Corpus: {vix.index[0].date()} → {vix.index[-1].date()} (n={len(vix)} days)")

    features = build_vix_vrp_features(vix, vxx, svxy)
    svxy_ret = svxy.pct_change().fillna(0)

    print()
    print("=" * 100)
    print(f"{'Variant':<55} {'CAGR':>7} {'Sharpe':>7} {'maxDD':>8} {'%inMkt':>8} {'n_trades':>10}")
    print("=" * 100)

    # ===== V1 : SVXY buy-and-hold =====
    pos_v1 = pd.Series(1.0, index=svxy.index)
    pos_v1.iloc[0] = 0  # virtual entry day 1
    strat_v1, trades_v1 = trades_from_position(svxy_ret, pos_v1)
    m_v1 = compute_metrics(strat_v1, pos_v1, "V1 SVXY buy-and-hold")
    print(f"{m_v1['label']:<55} {m_v1['CAGR_pct']:>6.2f}% {m_v1['Sharpe_ann']:>+7.2f} "
          f"{m_v1['max_DD_pct']:>+7.1f}% {m_v1['pct_time_in_market']:>7.1f}% {len(trades_v1):>10}")

    # ===== V2 : SVXY long if VIX prior < 25 =====
    pos_v2 = (features["vix_level_prior"] < 25).astype(float).fillna(0)
    strat_v2, trades_v2 = trades_from_position(svxy_ret, pos_v2)
    m_v2 = compute_metrics(strat_v2, pos_v2, "V2 SVXY long if VIX_prior<25 else cash")
    print(f"{m_v2['label']:<55} {m_v2['CAGR_pct']:>6.2f}% {m_v2['Sharpe_ann']:>+7.2f} "
          f"{m_v2['max_DD_pct']:>+7.1f}% {m_v2['pct_time_in_market']:>7.1f}% {len(trades_v2):>10}")

    # ===== V3 : SVXY long if VIX prior < 20 AND vxx_svxy_zscore < 0 =====
    cond_v3 = ((features["vix_level_prior"] < 20) &
               (features["vxx_svxy_zscore_20d"] < 0))
    pos_v3 = cond_v3.astype(float).fillna(0)
    strat_v3, trades_v3 = trades_from_position(svxy_ret, pos_v3)
    m_v3 = compute_metrics(strat_v3, pos_v3, "V3 SVXY long if VIX<20 AND zscore<0")
    print(f"{m_v3['label']:<55} {m_v3['CAGR_pct']:>6.2f}% {m_v3['Sharpe_ann']:>+7.2f} "
          f"{m_v3['max_DD_pct']:>+7.1f}% {m_v3['pct_time_in_market']:>7.1f}% {len(trades_v3):>10}")

    # SPY reference
    spy = pd.read_parquet(F2_DIR / "SPY_1d.parquet")
    spy["date"] = pd.to_datetime(spy["date"])
    spy = spy.set_index("date")["Close"]
    spy_ret = spy.pct_change().fillna(0).loc[vix.index]
    spy_eq = (1 + spy_ret).cumprod()
    years = (spy.index[-1] - spy.index[0]).total_seconds() / (86400 * 365)
    spy_cagr = (spy_eq.iloc[-1]) ** (1/years) - 1
    spy_sharpe = spy_ret.mean() / spy_ret.std() * np.sqrt(252)
    rm = spy_eq.expanding().max()
    spy_dd = (spy_eq / rm - 1).min()
    print(f"{'REF SPY buy-and-hold':<55} {spy_cagr*100:>6.2f}% {spy_sharpe:>+7.2f} "
          f"{spy_dd*100:>+7.1f}% {'100.0':>7}% {1:>10}")

    print()
    print("=" * 100)
    print("Niveau exploitation — capture_summary par variante")
    print("=" * 100)

    for label, trades in [("V1 buy-and-hold", trades_v1),
                           ("V2 VIX<25", trades_v2),
                           ("V3 VIX<20 + zscore<0", trades_v3)]:
        if len(trades) == 0:
            print(f"  {label:<30} no trades")
            continue
        s = capture_summary(trades[["r_multiple", "peak_r"]].dropna())
        print(f"  {label:<30} n={s['n']:<4} cap_med={s['median_capture_ratio']:>+7.3f} "
              f"%weak={s['pct_signal_weak']*100:>5.1f}% %early={s['pct_exit_early']*100:>5.1f}% "
              f"%late={s['pct_exit_late']*100:>5.1f}% %eff={s['pct_efficient']*100:>5.1f}% "
              f"→ {s['headline']}")

    # Sub-sample stability
    print()
    print("=" * 100)
    print("Sub-sample stability — 2019-2022 vs 2022-2025")
    print("=" * 100)
    split_date = pd.Timestamp("2022-06-01", tz="UTC") if vix.index.tz else pd.Timestamp("2022-06-01")

    def sub(ret: pd.Series, start, end) -> tuple[float, float]:
        r = ret.loc[start:end].dropna()
        if len(r) < 5 or r.std() == 0:
            return 0.0, 0.0
        sh = r.mean() / r.std() * np.sqrt(252)
        eq = (1 + r).cumprod()
        ye = (r.index[-1] - r.index[0]).total_seconds() / (86400*365)
        cg = (eq.iloc[-1]) ** (1/ye) - 1 if ye > 0 else 0
        return float(sh), float(cg * 100)

    for label, strat in [("V1 buy-and-hold", strat_v1), ("V2 VIX<25", strat_v2),
                          ("V3 VIX<20+z<0", strat_v3)]:
        sh1, cg1 = sub(strat, vix.index[0], split_date)
        sh2, cg2 = sub(strat, split_date, vix.index[-1])
        delta_sh = sh2 - sh1
        print(f"  {label:<25} 2019-2022: Sharpe={sh1:>+5.2f} CAGR={cg1:>+6.1f}%  | "
              f"2022-2025: Sharpe={sh2:>+5.2f} CAGR={cg2:>+6.1f}%  | ΔSharpe={delta_sh:>+5.2f}")

    # Gate plan v4.0
    print()
    print("=" * 100)
    print("Gate plan S+1 (système + exploitation)")
    print("=" * 100)
    print(f"  V3 Sharpe ≥ 0.8 (PASS bar)              : "
          f"{'PASS' if m_v3['Sharpe_ann'] >= 0.8 else 'FAIL'} (got {m_v3['Sharpe_ann']:.2f})")
    print(f"  V3 max DD ≤ -20%                        : "
          f"{'PASS' if m_v3['max_DD_pct'] >= -20 else 'FAIL'} (got {m_v3['max_DD_pct']:.1f}%)")
    s_v3 = capture_summary(trades_v3[['r_multiple', 'peak_r']].dropna()) if len(trades_v3) > 0 else {}
    print(f"  V3 capture_median ≥ 0.6 (exploitation)  : "
          f"{'PASS' if s_v3.get('median_capture_ratio', 0) >= 0.6 else 'FAIL'} "
          f"(got {s_v3.get('median_capture_ratio', 0):.3f})")
    print(f"  V3 headline ≠ signal_weak               : "
          f"{'PASS' if s_v3.get('headline') != 'signal_weak' else 'FAIL'} "
          f"(headline={s_v3.get('headline', 'n/a')})")


if __name__ == "__main__":
    main()
