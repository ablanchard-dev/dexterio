"""Sprint Ultra-Final T_final_2 — End-of-Day momentum SPY/QQQ.

Source académique : Heston-Korajczyk 2010 "Intraday Patterns in the
Cross-section of Stock Returns" — last 30min strength predicts overnight return.

Data gate PASSED : SPY/QQQ 1m 469 sessions (2024-06 → 2026-04, ~1.9y) > 250 min.

Règle pré-déclarée frozen :
  - Per trading day :
    * Compute last 30 min return (15:30-16:00 ET) = (close_16:00 - open_15:30) / open_15:30
    * Compute overnight return = (next_open_09:30 - close_16:00) / close_16:00
  - Signal : if last_30min_ret > 0 → long overnight, else flat
  - Costs : 6 bps round-trip (spread 1bp + slippage 5bp)
  - Benchmarks : buy-hold overnight only, buy-hold total (24h), cash

Critère PASS : Sharpe net > 0.7 + split stable + pas porté par 2-3 jours + permutation p<0.10
Critère KILL : Sharpe < 0.3 OR pire que buy-hold overnight
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

backend_dir = Path(__file__).resolve().parent.parent.parent
DATA = backend_dir / "data" / "market"

ET = ZoneInfo("America/New_York")
COST_BPS_RT = 6.0  # round-trip
N_PERMUTATIONS = 500
SEED = 42


def load_1m_data(asset: str) -> pd.DataFrame:
    df = pd.read_parquet(DATA / f"{asset}_1m.parquet")
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.sort_values("datetime").reset_index(drop=True)
    return df


def compute_eod_signal_per_day(df: pd.DataFrame) -> pd.DataFrame:
    """For each trading day, compute :
      - last_30min_ret : (close_16:00 - open_15:30) / open_15:30
      - overnight_ret : (next_open_09:30 - close_16:00) / close_16:00
    Returns DataFrame with one row per trading day.
    """
    df = df.copy()
    # Convert UTC → ET
    df["dt_et"] = df["datetime"].dt.tz_convert(ET)
    df["date_et"] = df["dt_et"].dt.date
    df["time_et"] = df["dt_et"].dt.time

    records = []
    days = sorted(df["date_et"].unique())
    for i, day in enumerate(days):
        day_data = df[df["date_et"] == day]
        # Last 30 min : 15:30-16:00 ET
        last_30 = day_data[
            (day_data["dt_et"].dt.hour == 15) & (day_data["dt_et"].dt.minute >= 30)
            | (day_data["dt_et"].dt.hour == 16) & (day_data["dt_et"].dt.minute == 0)
        ]
        if len(last_30) < 5:  # need at least 5 minutes of last 30
            continue
        # 15:30 open : first bar in window
        # 16:00 close : last bar
        last_30_sorted = last_30.sort_values("dt_et")
        bar_15_30 = last_30_sorted.iloc[0]
        bar_close = last_30_sorted.iloc[-1]
        last_30min_ret = bar_close["close"] / bar_15_30["open"] - 1

        # Next day open : first bar of next trading day at 9:30 ET
        if i + 1 >= len(days):
            continue
        next_day = days[i + 1]
        next_day_data = df[df["date_et"] == next_day]
        next_open_bars = next_day_data[
            (next_day_data["dt_et"].dt.hour == 9) & (next_day_data["dt_et"].dt.minute == 30)
        ]
        if next_open_bars.empty:
            # fallback : first bar of next day
            next_open_bar = next_day_data.sort_values("dt_et").iloc[0]
        else:
            next_open_bar = next_open_bars.sort_values("dt_et").iloc[0]
        overnight_ret = next_open_bar["open"] / bar_close["close"] - 1

        records.append({
            "date": day,
            "last_30min_ret": last_30min_ret,
            "overnight_ret": overnight_ret,
        })
    return pd.DataFrame(records)


def apply_signal(events: pd.DataFrame, threshold: float = 0.0,
                 cost_bps_rt: float = COST_BPS_RT) -> pd.Series:
    """Long overnight if last_30min_ret > threshold, else flat. Apply costs on signal=1."""
    signal = (events["last_30min_ret"] > threshold).astype(float)
    cost = signal * (cost_bps_rt / 10000.0)  # round-trip cost on entry+exit each long day
    strat_ret = signal * events["overnight_ret"] - cost
    strat_ret.index = pd.to_datetime(events["date"])
    return strat_ret


def metrics(rets: pd.Series, label: str) -> dict:
    rets = rets.dropna()
    if len(rets) < 30:
        return {"label": label, "valid": False, "n_days": len(rets)}
    eq = (1 + rets).cumprod()
    final_ret = eq.iloc[-1] - 1
    days = (rets.index[-1] - rets.index[0]).days
    years = days / 365.25
    cagr = (1 + final_ret) ** (1 / years) - 1 if years > 0 else 0
    sharpe = rets.mean() / rets.std() * np.sqrt(252) if rets.std() > 0 else 0
    rm = eq.expanding().max()
    dd = float((eq / rm - 1).min())
    calmar = cagr / abs(dd) if dd < 0 else 0
    n_active = int((rets != 0).sum())
    return {
        "label": label, "valid": True, "n_days": len(rets), "n_active": n_active,
        "CAGR_pct": cagr * 100, "Sharpe_ann": float(sharpe),
        "max_DD_pct": dd * 100, "Calmar": calmar,
        "vol_ann_pct": rets.std() * np.sqrt(252) * 100,
        "pct_active": float(n_active / len(rets) * 100) if len(rets) > 0 else 0,
    }


def main() -> None:
    print("=" * 100)
    print("Sprint Ultra-Final T_final_2 — EOD momentum SPY/QQQ (Heston-Korajczyk 2010)")
    print("=" * 100)

    for asset in ["SPY", "QQQ"]:
        print(f"\n=== {asset} ===")
        df = load_1m_data(asset)
        events = compute_eod_signal_per_day(df)
        print(f"  Loaded {len(df):,} 1m bars, {len(events)} trading day events")
        if events.empty:
            print(f"  ❌ No events extracted — data gate fail")
            continue

        # Strategy : long overnight if last_30min_ret > 0
        strat_rets = apply_signal(events, threshold=0.0, cost_bps_rt=COST_BPS_RT)

        # Benchmarks
        all_overnight = events["overnight_ret"].rename("buy-hold-overnight")
        all_overnight.index = pd.to_datetime(events["date"])

        m_strat = metrics(strat_rets, f"{asset} EOD momentum (long if last_30min>0)")
        m_overnight = metrics(all_overnight, f"REF {asset} buy-hold overnight only")

        # Asset buy-hold total (using daily close-to-close from 1m data)
        df["dt_et"] = df["datetime"].dt.tz_convert(ET)
        df["date_et"] = df["dt_et"].dt.date
        daily_close = df.groupby("date_et")["close"].last()
        daily_close.index = pd.to_datetime(daily_close.index)
        bh_rets = daily_close.pct_change().dropna()
        m_bh = metrics(bh_rets, f"REF {asset} buy-hold total (daily close)")

        print(f"\n  {'Strategy':<55} {'CAGR':>7} {'Sharpe':>7} {'maxDD':>8} {'Calmar':>7} {'%active':>8}")
        print("  " + "=" * 95)
        for m in [m_strat, m_overnight, m_bh]:
            if not m.get("valid"):
                print(f"  {m['label']:<55} INVALID")
                continue
            print(f"  {m['label']:<55} {m['CAGR_pct']:>6.2f}% {m['Sharpe_ann']:>+7.2f} "
                  f"{m['max_DD_pct']:>+7.1f}% {m['Calmar']:>+7.2f} "
                  f"{m['pct_active']:>7.1f}%")

        # Sub-sample : split at midpoint
        mid = len(strat_rets) // 2
        sub1 = strat_rets.iloc[:mid].dropna()
        sub2 = strat_rets.iloc[mid:].dropna()
        sh1 = sub1.mean() / sub1.std() * np.sqrt(252) if sub1.std() > 0 else 0
        sh2 = sub2.mean() / sub2.std() * np.sqrt(252) if sub2.std() > 0 else 0
        print(f"\n  Sub-sample : early Sharpe={sh1:+.2f} | late Sharpe={sh2:+.2f} | "
              f"ΔSharpe={sh2-sh1:+.2f}")

        # Permutation 500 iter (only if not clean fail)
        sh = m_strat["Sharpe_ann"]
        if sh >= 0.3 and sh > m_overnight["Sharpe_ann"]:
            print(f"\n  Borderline → running permutation 500 iter...")
            rng = np.random.default_rng(SEED)
            real_sharpe = sh
            perm_sharpes = []
            for i in range(N_PERMUTATIONS):
                # Shuffle the relationship : permute last_30min_ret only, keep overnight
                shuffled_signal = events["last_30min_ret"].sample(frac=1, random_state=int(rng.integers(0, 1e9))).reset_index(drop=True)
                temp_events = events.copy()
                temp_events["last_30min_ret"] = shuffled_signal.values
                perm_rets = apply_signal(temp_events, threshold=0.0, cost_bps_rt=COST_BPS_RT)
                perm_rets_clean = perm_rets.dropna()
                if len(perm_rets_clean) > 30 and perm_rets_clean.std() > 0:
                    perm_sharpes.append(perm_rets_clean.mean() / perm_rets_clean.std() * np.sqrt(252))
            perm_sharpes = np.array(perm_sharpes)
            p_value = float((perm_sharpes >= real_sharpe).mean())
            print(f"  Real Sharpe : {real_sharpe:.3f} vs perm mean : {perm_sharpes.mean():.3f} "
                  f"std : {perm_sharpes.std():.3f}")
            print(f"  p-value : {p_value:.4f}  (PASS gate p<0.10 : {'PASS' if p_value < 0.10 else 'FAIL'})")
        else:
            print(f"\n  Clean fail (Sharpe={sh:.2f} < 0.3 or worse than overnight bench), permutation skipped")

        # Gate
        print(f"\n  Gate verdict {asset} :")
        print(f"    Sharpe ≥ 0.7 (PASS bar) : {'PASS' if sh >= 0.7 else 'FAIL'} (got {sh:.2f})")
        print(f"    Sharpe ≥ 0.3 (kill) : {'OK' if sh >= 0.3 else 'KILL'} (got {sh:.2f})")
        print(f"    Beat buy-hold overnight ({m_overnight['Sharpe_ann']:.2f}) : "
              f"{'PASS' if sh > m_overnight['Sharpe_ann'] else 'FAIL'}")

        # Save
        out_dir = backend_dir / "results" / f"ultra_final_t2_eod_{asset.lower()}"
        out_dir.mkdir(parents=True, exist_ok=True)
        events.to_parquet(out_dir / "events.parquet", index=False)
        pd.DataFrame({
            "strat_eq": (1 + strat_rets).cumprod(),
            "overnight_eq": (1 + all_overnight).cumprod(),
        }).to_parquet(out_dir / "equity_curves.parquet")
        print(f"  [saved → {out_dir}]")


if __name__ == "__main__":
    main()
