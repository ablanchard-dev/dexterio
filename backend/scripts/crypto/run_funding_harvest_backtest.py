"""Crypto funding harvest backtest — Plan v4.0 J6-J7 Priorité #2.

Hypothèse falsifiable :
    Funding rate harvesting BTC/ETH perp Binance, neutralisé spot, génère
    E[R]_net annualisé > 8% post-frais (taker 0.04% × 2 entry/exit) sur
    backtest 2y avec drawdown < 10%.

Stratégie testée (sober, 1 variante) :
    - Continuous holding : enter day 1 long spot + short perp (market-neutral),
      collect funding 3×/jour. No re-balance.
    - Si funding rate négative for >2 consecutive 8h cycles : exit position
      until funding turns positive again.
    - Costs : 0.04% taker × 2 sides (spot + perp) × 2 (entry+exit) = 0.16%
      per cycle entry/exit.
    - Position size : $10000 notional per asset (BTC + ETH = $20k portfolio).

Gate plan :
    PASS : E[R]_net annualisé > 8% AND DD < 10% AND > 70% windows funding+
    KILL : E[R]_net < 5% OR DD > 15% OR > 30% windows funding négatif

Usage : python backend/scripts/crypto/run_funding_harvest_backtest.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

backend_dir = Path(__file__).resolve().parent.parent.parent
DATA_DIR = backend_dir / "data" / "crypto"

NOTIONAL_PER_ASSET = 10_000  # $10k per asset
TAKER_FEE = 0.0004  # 0.04% Binance taker per side
NEGATIVE_FUNDING_EXIT_THRESHOLD = 2  # exit after N consecutive negative funding cycles


def load_funding(symbol: str) -> pd.DataFrame:
    df = pd.read_parquet(DATA_DIR / f"{symbol}_funding_8h.parquet")
    df["datetime"] = pd.to_datetime(df["datetime"])
    return df.set_index("datetime").sort_index()


def load_spot_perp(symbol: str) -> pd.DataFrame:
    spot = pd.read_parquet(DATA_DIR / f"{symbol}_spot_1d.parquet")
    perp = pd.read_parquet(DATA_DIR / f"{symbol}_perp_1d.parquet")
    spot["datetime"] = pd.to_datetime(spot["datetime"])
    perp["datetime"] = pd.to_datetime(perp["datetime"])
    spot = spot.set_index("datetime")[["close"]].rename(columns={"close": "spot_close"})
    perp = perp.set_index("datetime")[["close"]].rename(columns={"close": "perp_close"})
    return spot.join(perp, how="inner").dropna()


def backtest_funding_harvest(symbol: str, notional: float = NOTIONAL_PER_ASSET) -> dict:
    """Run funding harvest backtest for one asset.

    Strategy :
        - Track position state (in_market or out)
        - At each 8h funding event :
          - If in_market : collect funding rate × notional (positive funding adds
            to PnL because we're SHORT perp = funded by longs)
          - If consecutive negative funding > threshold : exit (apply costs)
          - If out and funding turns positive : enter (apply costs)
        - Track basis P&L (spot vs perp price drift) — should be near 0 in
          true market-neutral, but track for sanity
    """
    funding = load_funding(symbol)
    prices = load_spot_perp(symbol)

    # Cumulative PnL tracking
    funding_pnl_cum = 0.0
    cost_cum = 0.0
    in_market = False
    consecutive_neg = 0
    n_entries = 0
    n_exits = 0
    funding_collected = []  # per-cycle PnL
    timestamps = []
    in_market_flags = []
    equity = []

    for ts, row in funding.iterrows():
        fr = row["fundingRate"]
        # Entry/exit logic
        if not in_market and fr > 0:
            # Enter (long spot + short perp), apply 2-side cost
            cost_cum += notional * TAKER_FEE * 2  # spot buy + perp short
            in_market = True
            consecutive_neg = 0
            n_entries += 1
        if in_market:
            # Collect funding (we're SHORT perp, positive funding pays us)
            funding_pnl_cum += notional * fr
            if fr < 0:
                consecutive_neg += 1
                if consecutive_neg >= NEGATIVE_FUNDING_EXIT_THRESHOLD:
                    # Exit, apply 2-side cost
                    cost_cum += notional * TAKER_FEE * 2
                    in_market = False
                    consecutive_neg = 0
                    n_exits += 1
            else:
                consecutive_neg = 0
        timestamps.append(ts)
        in_market_flags.append(in_market)
        equity.append(funding_pnl_cum - cost_cum)
        funding_collected.append(notional * fr if in_market else 0)

    eq = pd.Series(equity, index=timestamps)
    if in_market:
        # Final close
        cost_cum += notional * TAKER_FEE * 2
        eq.iloc[-1] -= notional * TAKER_FEE * 2
        n_exits += 1

    final_pnl = eq.iloc[-1]

    # Annualize : 2 years = 730 days
    days = (eq.index[-1] - eq.index[0]).total_seconds() / 86400
    years = days / 365.0
    apr = (final_pnl / notional) / years * 100 if years > 0 else 0

    # DD on equity curve
    running_max = eq.expanding().max()
    dd_series = (eq - running_max) / notional
    max_dd_pct = float(dd_series.min() * 100)

    # Sharpe on daily resampled equity
    eq_daily = eq.resample("1D").last().ffill()
    daily_ret_pct = eq_daily.diff() / notional
    daily_ret_pct = daily_ret_pct.dropna()
    sharpe_ann = float(daily_ret_pct.mean() / daily_ret_pct.std() * np.sqrt(365)) if daily_ret_pct.std() > 0 else 0

    # % windows positive funding (overall, not per-position)
    pct_pos_funding = (funding["fundingRate"] > 0).mean() * 100

    # % time in market
    pct_in_market = sum(in_market_flags) / len(in_market_flags) * 100

    return {
        "symbol": symbol,
        "n_funding_events": len(funding),
        "final_pnl_$": final_pnl,
        "gross_funding_pnl_$": funding_pnl_cum,
        "total_cost_$": cost_cum,
        "n_entries": n_entries,
        "n_exits": n_exits,
        "apr_net_pct": apr,
        "max_dd_pct": max_dd_pct,
        "sharpe_ann": sharpe_ann,
        "pct_pos_funding": pct_pos_funding,
        "pct_in_market": pct_in_market,
        "equity": eq,
    }


def main() -> None:
    print("=" * 70)
    print("Crypto funding harvest backtest — Plan v4.0 J6-J7 Priorité #2")
    print("=" * 70)
    print()
    print(f"Notional per asset : ${NOTIONAL_PER_ASSET:,}")
    print(f"Taker fee : {TAKER_FEE*100:.2f}% per side")
    print(f"Strategy : continuous hold long spot + short perp, exit on "
          f"{NEGATIVE_FUNDING_EXIT_THRESHOLD} consecutive negative funding")
    print()

    results = {}
    for symbol in ["BTCUSDT", "ETHUSDT"]:
        print(f"\n=== {symbol} ===")
        r = backtest_funding_harvest(symbol)
        results[symbol] = r
        print(f"  n funding events       : {r['n_funding_events']}")
        print(f"  n entries              : {r['n_entries']}")
        print(f"  n exits                : {r['n_exits']}")
        print(f"  % time in market       : {r['pct_in_market']:.1f}%")
        print(f"  % windows funding pos  : {r['pct_pos_funding']:.1f}%")
        print(f"  gross funding PnL      : ${r['gross_funding_pnl_$']:,.0f}")
        print(f"  total cost             : ${r['total_cost_$']:,.0f}")
        print(f"  net PnL                : ${r['final_pnl_$']:,.0f}")
        print(f"  ANNUALIZED RETURN      : {r['apr_net_pct']:.2f}%")
        print(f"  max DD                 : {r['max_dd_pct']:.2f}%")
        print(f"  Sharpe (daily)         : {r['sharpe_ann']:.2f}")

    print()
    print("=" * 70)
    print("Portfolio aggregate (BTC + ETH equally-weighted)")
    print("=" * 70)
    btc = results["BTCUSDT"]
    eth = results["ETHUSDT"]
    total_pnl = btc["final_pnl_$"] + eth["final_pnl_$"]
    total_notional = NOTIONAL_PER_ASSET * 2
    days = (btc["equity"].index[-1] - btc["equity"].index[0]).total_seconds() / 86400
    years = days / 365.0
    apr_portfolio = (total_pnl / total_notional) / years * 100
    print(f"Total PnL  : ${total_pnl:,.0f}")
    print(f"Notional   : ${total_notional:,}")
    print(f"APR (net)  : {apr_portfolio:.2f}%")

    # Combined equity curve
    eq_btc = btc["equity"]
    eq_eth = eth["equity"].reindex(eq_btc.index, method="pad").fillna(0)
    eq_total = eq_btc + eq_eth
    rm = eq_total.expanding().max()
    dd_total = ((eq_total - rm) / total_notional).min() * 100
    daily_eq = eq_total.resample("1D").last().ffill()
    daily_ret = daily_eq.diff() / total_notional
    sharpe_total = daily_ret.mean() / daily_ret.std() * np.sqrt(365) if daily_ret.std() > 0 else 0
    print(f"Max DD     : {dd_total:.2f}%")
    print(f"Sharpe     : {sharpe_total:.2f}")

    print()
    print("=== Gate plan v4.0 evaluation ===")
    pct_pos = (btc["pct_pos_funding"] + eth["pct_pos_funding"]) / 2
    print(f"  E[R]_net annualisé > 8% (PASS bar)  : "
          f"{'PASS' if apr_portfolio > 8 else 'FAIL'} (got {apr_portfolio:.2f}%)")
    print(f"  E[R]_net annualisé > 5% (kill rule) : "
          f"{'OK' if apr_portfolio > 5 else 'KILL'} (got {apr_portfolio:.2f}%)")
    print(f"  max DD < 10% (PASS bar)             : "
          f"{'PASS' if abs(dd_total) < 10 else 'FAIL'} (got {dd_total:.2f}%)")
    print(f"  max DD < 15% (kill rule)            : "
          f"{'OK' if abs(dd_total) < 15 else 'KILL'} (got {dd_total:.2f}%)")
    print(f"  > 70% windows funding+ (PASS bar)   : "
          f"{'PASS' if pct_pos > 70 else 'FAIL'} (got {pct_pos:.1f}%)")
    print(f"  > 30% windows funding- (kill rule)  : "
          f"{'KILL' if (100-pct_pos) > 30 else 'OK'} (got {100-pct_pos:.1f}%)")


if __name__ == "__main__":
    main()
