"""S+3-bis T4 — Donchian breakout daily per-asset.

Idée corpus : Turtle traders (Richard Dennis 1983) classique trend-following.
User correction : signal failed sur SPY peut PASS sur asset moins arbitré.

Signal pré-déclaré frozen (1 SEUL, pas variantes) :
  - Long quand close > 20-day high (rolling)
  - Exit quand close < 10-day low
  - Long-only, no SL fixed (Donchian only)

Assets pré-déclarés : QQQ + GLD + BTC daily + SPY (control)
4 verdicts indépendants per asset.

Verdict per asset :
  - PASS : Sharpe > 0.6 + beat buy-hold + permutation p<0.10 si borderline
  - KILL : Sharpe < 0.3
  - 1+/4 PASS = intuition validée empiriquement asset-specific edge
  - 0/4 PASS = signal class mort universellement
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

backend_dir = Path(__file__).resolve().parent.parent.parent
DATA_F2 = backend_dir / "data" / "f2_daily"
DATA_CRYPTO = backend_dir / "data" / "crypto"

DONCHIAN_HIGH_DAYS = 20
DONCHIAN_LOW_DAYS = 10
COST_BPS = 5.0


def load_asset(asset: str) -> pd.Series:
    if asset == "SPY":
        df = pd.read_parquet(DATA_F2 / "SPY_1d.parquet")
        df["date"] = pd.to_datetime(df["date"])
        return df.set_index("date")["Close"].sort_index()
    if asset == "QQQ":
        df = pd.read_parquet(DATA_F2 / "QQQ_1d.parquet")
        df["date"] = pd.to_datetime(df["date"])
        return df.set_index("date")["Close"].sort_index()
    if asset == "GLD":
        df = pd.read_parquet(DATA_F2 / "GLD_1d.parquet")
        df["date"] = pd.to_datetime(df["date"])
        return df.set_index("date")["Close"].sort_index()
    if asset == "BTC":
        df = pd.read_parquet(DATA_CRYPTO / "BTCUSDT_spot_1d_6.5y.parquet")
        df["datetime"] = pd.to_datetime(df["datetime"])
        df["date"] = df["datetime"].dt.tz_localize(None).dt.normalize()
        return df.set_index("date")["close"].sort_index()
    raise ValueError(asset)


def donchian_strategy(prices: pd.Series, high_days: int = DONCHIAN_HIGH_DAYS,
                       low_days: int = DONCHIAN_LOW_DAYS,
                       cost_bps: float = COST_BPS) -> tuple[pd.Series, pd.Series, dict]:
    """Long-only Donchian breakout."""
    rolling_high = prices.rolling(high_days).max()
    rolling_low = prices.rolling(low_days).min()
    rets = prices.pct_change().fillna(0)

    position = pd.Series(0.0, index=prices.index)
    cur_pos = 0
    for i in range(len(prices)):
        if pd.isna(rolling_high.iloc[i]) or pd.isna(rolling_low.iloc[i]):
            continue
        price = prices.iloc[i]
        if cur_pos == 0:
            # Entry on breakout (close > 20d high)
            if price > rolling_high.iloc[max(0, i-1)]:  # use prior high
                cur_pos = 1
        else:
            # Exit when close < 10d low
            if price < rolling_low.iloc[max(0, i-1)]:
                cur_pos = 0
        position.iloc[i] = cur_pos

    daily_strat = position.shift(1).fillna(0) * rets
    pos_change = position.diff().abs().fillna(0)
    cost = pos_change * (cost_bps / 10000.0)
    daily_strat_net = daily_strat - cost

    n_trades = int((pos_change != 0).sum() / 2)
    pct_in = float(position.mean() * 100)
    return daily_strat_net, position, {"n_trades": n_trades, "pct_in_market": pct_in}


def metrics(rets: pd.Series, label: str) -> dict:
    rets = rets.dropna()
    if len(rets) < 30:
        return {"label": label, "valid": False}
    eq = (1 + rets).cumprod()
    days = (rets.index[-1] - rets.index[0]).days
    years = days / 365.25
    cagr = eq.iloc[-1] ** (1 / years) - 1 if years > 0 else 0
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
    assets = ["QQQ", "GLD", "BTC", "SPY"]
    print("=" * 110)
    print(f"S+3-bis T4 — Donchian breakout daily ({DONCHIAN_HIGH_DAYS}d high / {DONCHIAN_LOW_DAYS}d low) per asset")
    print("=" * 110)

    all_results = []
    for asset in assets:
        prices = load_asset(asset)
        bh_rets = prices.pct_change().fillna(0)
        bh = metrics(bh_rets, f"{asset} buy-hold")
        strat_rets, pos, stats = donchian_strategy(prices)
        m = metrics(strat_rets, f"{asset} Donchian")

        beat_bh = m["Sharpe_ann"] > bh["Sharpe_ann"]
        pass_gate = m["Sharpe_ann"] >= 0.6 and beat_bh
        kill = m["Sharpe_ann"] < 0.3
        verdict = "PASS" if pass_gate else ("KILL" if kill else "MARGINAL")

        print(f"\n=== {asset} (n={len(prices)}) ===")
        print(f"  Buy-hold ref  : Sharpe={bh['Sharpe_ann']:+.3f} CAGR={bh['CAGR_pct']:+.2f}% "
              f"DD={bh['max_DD_pct']:+.1f}% Calmar={bh['Calmar']:+.2f}")
        print(f"  Donchian strat: Sharpe={m['Sharpe_ann']:+.3f} CAGR={m['CAGR_pct']:+.2f}% "
              f"DD={m['max_DD_pct']:+.1f}% Calmar={m['Calmar']:+.2f}  "
              f"trades={stats['n_trades']} %in={stats['pct_in_market']:.0f}%")
        print(f"  Beat buy-hold : {beat_bh}  → **{verdict}**")

        # Sub-sample
        split_date = pd.Timestamp("2022-06-01")
        sub1 = strat_rets.loc[strat_rets.index[0]:split_date].dropna()
        sub2 = strat_rets.loc[split_date:strat_rets.index[-1]].dropna()
        sh1 = sub1.mean() / sub1.std() * np.sqrt(252) if sub1.std() > 0 else 0
        sh2 = sub2.mean() / sub2.std() * np.sqrt(252) if sub2.std() > 0 else 0
        print(f"  Sub-sample : 2019-2022 Sharpe={sh1:+.2f}  | 2022-2025 Sharpe={sh2:+.2f}  | "
              f"ΔSharpe={sh2-sh1:+.2f}")

        all_results.append({
            "asset": asset, "Sharpe": m["Sharpe_ann"], "CAGR_pct": m["CAGR_pct"],
            "max_DD_pct": m["max_DD_pct"], "Calmar": m["Calmar"],
            "n_trades": stats["n_trades"], "pct_in_market": stats["pct_in_market"],
            "bh_Sharpe": bh["Sharpe_ann"], "beat_bh": beat_bh,
            "verdict": verdict, "sub_2019_2022_sharpe": sh1, "sub_2022_2025_sharpe": sh2,
        })

    # Cross-asset summary
    print()
    print("=" * 110)
    print("Cross-asset summary T4 Donchian breakout")
    print("=" * 110)
    df = pd.DataFrame(all_results)
    n_pass = (df["verdict"] == "PASS").sum()
    n_kill = (df["verdict"] == "KILL").sum()
    n_marg = (df["verdict"] == "MARGINAL").sum()
    print(f"  PASS={n_pass}/4  KILL={n_kill}  MARGINAL={n_marg}")
    if n_pass >= 1:
        print(f"  ✅ Asset-specific edge validé empiriquement (intuition user)")
    else:
        print(f"  ❌ 0/4 PASS = signal class Donchian breakout mort universellement")

    out_dir = backend_dir / "results" / "s3bis_t4_donchian"
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_dir / "results.parquet", index=False)
    print(f"\n[saved → {out_dir}]")


if __name__ == "__main__":
    main()
