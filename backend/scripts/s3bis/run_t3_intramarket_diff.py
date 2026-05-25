"""S+3-bis T3 — Intramarket SPY-QQQ differential standalone signal.

Idée corpus : n2mY86S01fg intramarket differencing.

Asset naturel : pair SPY-QQQ.

Règle pré-déclarée frozen :
  - diff = (logret_spy - logret_qqq) / (atr_spy_norm × sqrt(lookback_20))
  - z-score rolling 60d
  - Long SPY/short QQQ quand z < -2.0
  - Mirror (short SPY/long QQQ) quand z > +2.0
  - Hold jusqu'à |z| < 0.5
  - Beta-neutral sizing (50/50 dollar exposure)
  - 5 bps cost per leg per side

Benchmark : SPY buy-hold + 50/50 SPY-QQQ portfolio control.

Verdict : PASS si Sharpe > 0.7 + beat 2 benchmarks + permutation p<0.10 si borderline.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

backend_dir = Path(__file__).resolve().parent.parent.parent
DATA_F2 = backend_dir / "data" / "f2_daily"

LOOKBACK_DIFF = 20
LOOKBACK_ZSCORE = 60
Z_ENTRY = 2.0
Z_EXIT = 0.5
COST_BPS = 5.0


def compute_atr(prices: pd.DataFrame, period: int = 14) -> pd.Series:
    """Simple ATR using close-to-close range."""
    rets = prices.pct_change().abs()
    return rets.rolling(period).mean()


def main() -> None:
    print("=" * 100)
    print("S+3-bis T3 — Intramarket SPY-QQQ differential standalone")
    print("=" * 100)

    spy_df = pd.read_parquet(DATA_F2 / "SPY_1d.parquet")
    spy_df["date"] = pd.to_datetime(spy_df["date"])
    spy = spy_df.set_index("date")["Close"].sort_index()

    qqq_df = pd.read_parquet(DATA_F2 / "QQQ_1d.parquet")
    qqq_df["date"] = pd.to_datetime(qqq_df["date"])
    qqq = qqq_df.set_index("date")["Close"].sort_index()

    common = spy.index.intersection(qqq.index)
    spy, qqq = spy.loc[common], qqq.loc[common]
    print(f"Data : {common.min().date()} → {common.max().date()} ({len(common)} days)")

    # Compute differential signal
    spy_logret = np.log(spy / spy.shift(1))
    qqq_logret = np.log(qqq / qqq.shift(1))
    spy_atr = compute_atr(spy.to_frame("close")["close"], 14)
    diff = (spy_logret - qqq_logret) / (spy_atr * np.sqrt(LOOKBACK_DIFF))
    diff = diff.replace([np.inf, -np.inf], np.nan).dropna()

    # Rolling z-score
    rolling_mean = diff.rolling(LOOKBACK_ZSCORE).mean()
    rolling_std = diff.rolling(LOOKBACK_ZSCORE).std()
    z = (diff - rolling_mean) / rolling_std
    z = z.dropna()
    print(f"Z-score series : n={len(z)}, mean={z.mean():.3f}, std={z.std():.3f}, "
          f"p10={z.quantile(0.1):.2f}, p90={z.quantile(0.9):.2f}")

    # Generate position signal :
    # Position = -1 long SPY/short QQQ (when z < -Z_ENTRY), +1 short SPY/long QQQ (when z > Z_ENTRY)
    # Exit when |z| < Z_EXIT
    position = pd.Series(0.0, index=z.index)
    cur_pos = 0
    for i, val in enumerate(z.values):
        if cur_pos == 0:
            if val < -Z_ENTRY:
                cur_pos = -1  # long spread (long SPY/short QQQ)
            elif val > Z_ENTRY:
                cur_pos = 1   # short spread
        else:
            if abs(val) < Z_EXIT:
                cur_pos = 0
        position.iloc[i] = cur_pos

    # Compute strategy returns
    # Spread return = spy_ret - qqq_ret (long SPY/short QQQ if pos = -1, mirror if +1)
    spy_ret = spy.pct_change().fillna(0).reindex(z.index).fillna(0)
    qqq_ret = qqq.pct_change().fillna(0).reindex(z.index).fillna(0)
    spread_ret = spy_ret - qqq_ret  # long SPY/short QQQ daily return
    # Strategy : when pos = -1, we're long spread → +spread_ret
    #            when pos = +1, we're short spread → -spread_ret
    daily_strat = -position.shift(1).fillna(0) * spread_ret  # negative because pos -1 = long spread

    # Cost on position changes
    pos_change = position.diff().abs().fillna(0)
    # Each leg trade = both SPY and QQQ → 2 sides cost
    cost = pos_change * 2 * (COST_BPS / 10000.0)
    daily_strat_net = daily_strat - cost

    # Stats
    n_trades = int((pos_change != 0).sum() / 2)  # entry + exit each = 2 changes
    pct_in_market = (position != 0).mean() * 100
    print(f"Strategy : {n_trades} round-trip trades, {pct_in_market:.1f}% time in market")

    # Metrics
    eq = (1 + daily_strat_net).cumprod()
    rets = daily_strat_net.dropna()
    sharpe = float(rets.mean() / rets.std() * np.sqrt(252)) if rets.std() > 0 else 0
    days = (rets.index[-1] - rets.index[0]).days
    years = days / 365.25
    cagr = (eq.iloc[-1]) ** (1/years) - 1 if years > 0 else 0
    rm = eq.expanding().max()
    max_dd = float((eq / rm - 1).min())
    calmar = cagr / abs(max_dd) if max_dd < 0 else 0

    # Benchmarks
    spy_eq = (1 + spy_ret.loc[z.index]).cumprod()
    spy_sharpe = spy_ret.loc[z.index].mean() / spy_ret.loc[z.index].std() * np.sqrt(252)
    spy_cagr = spy_eq.iloc[-1] ** (1/years) - 1 if years > 0 else 0
    spy_dd = (spy_eq / spy_eq.expanding().max() - 1).min()
    spy_calmar = spy_cagr / abs(spy_dd) if spy_dd < 0 else 0

    # 50/50 SPY-QQQ
    port_5050 = 0.5 * spy_ret.loc[z.index] + 0.5 * qqq_ret.loc[z.index]
    port_5050_eq = (1 + port_5050).cumprod()
    port_sharpe = port_5050.mean() / port_5050.std() * np.sqrt(252)
    port_cagr = port_5050_eq.iloc[-1] ** (1/years) - 1 if years > 0 else 0
    port_dd = (port_5050_eq / port_5050_eq.expanding().max() - 1).min()
    port_calmar = port_cagr / abs(port_dd) if port_dd < 0 else 0

    print()
    print("=" * 100)
    print(f"{'Strategy':<48} {'CAGR':>7} {'Sharpe':>7} {'maxDD':>8} {'Calmar':>7}")
    print("=" * 100)
    print(f"{'T3 SPY-QQQ differential mean-rev':<48} {cagr*100:>6.2f}% {sharpe:>+7.2f} "
          f"{max_dd*100:>+7.1f}% {calmar:>+7.2f}")
    print(f"{'REF SPY buy-hold':<48} {spy_cagr*100:>6.2f}% {spy_sharpe:>+7.2f} "
          f"{spy_dd*100:>+7.1f}% {spy_calmar:>+7.2f}")
    print(f"{'REF 50/50 SPY-QQQ':<48} {port_cagr*100:>6.2f}% {port_sharpe:>+7.2f} "
          f"{port_dd*100:>+7.1f}% {port_calmar:>+7.2f}")

    # Sub-sample
    split_date = pd.Timestamp("2022-06-01")
    print()
    print("Sub-sample :")
    for label, r in [("T3 differential", rets), ("SPY", spy_ret.loc[z.index]),
                       ("50/50", port_5050)]:
        sub1 = r.loc[r.index[0]:split_date].dropna()
        sub2 = r.loc[split_date:r.index[-1]].dropna()
        sh1 = sub1.mean() / sub1.std() * np.sqrt(252) if sub1.std() > 0 else 0
        sh2 = sub2.mean() / sub2.std() * np.sqrt(252) if sub2.std() > 0 else 0
        print(f"  {label:<25} 2019-2022: Sharpe={sh1:+.2f}  | 2022-2025: Sharpe={sh2:+.2f}  | "
              f"ΔSharpe={sh2-sh1:+.2f}")

    # Gate
    print()
    print("Gate plan S+3-bis T3 :")
    print(f"  Sharpe ≥ 0.7 (PASS bar) : {'PASS' if sharpe >= 0.7 else 'FAIL'} (got {sharpe:.2f})")
    print(f"  Sharpe ≥ 0.4 (kill rule) : {'OK' if sharpe >= 0.4 else 'KILL'} (got {sharpe:.2f})")
    print(f"  Sharpe > SPY ({spy_sharpe:.2f}) : {'PASS' if sharpe > spy_sharpe else 'FAIL'}")
    print(f"  Sharpe > 50/50 ({port_sharpe:.2f}) : {'PASS' if sharpe > port_sharpe else 'FAIL'}")
    print(f"  Calmar > SPY ({spy_calmar:.2f}) : {'PASS' if calmar > spy_calmar else 'FAIL'} (got {calmar:.2f})")

    # Save
    out_dir = backend_dir / "results" / "s3bis_t3_intramarket"
    out_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({
        "differential_strategy": eq,
        "SPY": spy_eq,
        "50_50_spy_qqq": port_5050_eq,
        "z_score": z,
        "position": position,
    }).to_parquet(out_dir / "equity_curves.parquet")
    print(f"\n[saved → {out_dir}]")


if __name__ == "__main__":
    main()
