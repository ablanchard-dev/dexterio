"""Stat arb SPY-QQQ v2 smoke harness (Leg 4.1 §0.5).

Structural change vs v1 (§10 r11 legal reopening):
  - Cointegration gate moved from intraday 5m 200-bar rolling → **daily
    rolling 60 trading days**. The daily coint result gates whether the
    5m z-score tracker arms on a given trading day (ON/OFF per day).
  - In v1 the intraday EG test at α=0.05 passed in 1/59 windows — too
    restrictive and non-informative. SPY-QQQ are structurally coint by
    construction; v2 tests that relation on daily closes where the
    multi-week structural stability actually lives.

Pipeline:
  1. Load 1m SPY + QQQ bars across load_start → end (≥120 calendar days
     to build 60-day daily coint window).
  2. Aggregate to 5m + daily closes (NY 16:00 ET close).
  3. Precompute daily_coint_regime dict: for each trading_date T, compute
     EG test on daily closes [T-60, T-1] (strictly prior, no lookahead).
     regime[T] = (p_value, is_coint).
  4. For each 5m bar in NY session during [start, end]:
       - if daily_coint_regime[ts.date()].is_coint == False → skip.
       - else compute rolling_beta, spread, z; feed PairSpreadTracker.
  5. On ARMED setup: simulate pair trade with z-score exits (TP |z|<=0.5,
     SL |z|>=3.0, time_stop 18 bars). Next-bar-open fills.
  6. Write trades.parquet + debug_counts.json + daily_coint_trace.json.

Reuses briques D1+D2 (cointegration, zscore, sizing, tracker) unchanged.
Only difference from v1 harness: the daily regime gate pre-computed
outside PairSpreadTracker, applied as an intraday skip condition.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from engines.stat_arb.cointegration import engle_granger_test  # noqa: E402
from engines.stat_arb.sizing import pair_sizing  # noqa: E402
from engines.stat_arb.tracker import PairSpreadTracker  # noqa: E402
from engines.stat_arb.zscore import (  # noqa: E402
    compute_spread,
    rolling_beta,
    rolling_zscore,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("stat_arb_smoke_v2")


@dataclass
class SmokeConfigV2:
    start_date: str = "2025-11-17"
    end_date: str = "2025-11-21"
    symbol_y: str = "SPY"
    symbol_x: str = "QQQ"
    spy_path: str = "backend/data/market/SPY_1m.parquet"
    qqq_path: str = "backend/data/market/QQQ_1m.parquet"
    session_start_utc: str = "14:30"   # 09:30 ET winter
    session_end_utc: str = "21:00"     # 16:00 ET winter
    beta_window: int = 60              # 5m bars (5h)
    z_window: int = 60
    # Daily regime gate
    daily_coint_window: int = 60       # trading days (~3 calendar months)
    daily_coint_alpha: float = 0.05
    daily_lookback_days: int = 120     # calendar days to load (covers 60 trading days + buffer)
    entry_z: float = 2.0
    exit_z: float = 0.5
    blowout_z: float = 3.0
    time_stop_bars: int = 18           # 1.5h
    lockout_bars: int = 6
    risk_dollars: float = 100.0
    label: str = "stat_arb_spy_qqq_v2_smoke_nov_w4"
    output_dir: str = "backend/results/labs/mini_week/stat_arb_spy_qqq_v2"


@dataclass
class PairTrade:
    pair_id: str
    entry_ts: datetime
    exit_ts: Optional[datetime]
    direction: str
    armed_z: float
    armed_beta: float
    entry_price_y: float
    entry_price_x: float
    exit_price_y: Optional[float]
    exit_price_x: Optional[float]
    qty_y: int
    qty_x: int
    exit_reason: Optional[str]
    exit_z: Optional[float]
    peak_pnl_dollars: float
    mae_pnl_dollars: float
    pnl_dollars: Optional[float]
    bars_held: int
    peak_r: float = 0.0
    mae_r: float = 0.0
    realized_r: Optional[float] = None
    daily_coint_pvalue: Optional[float] = None


def load_1m(path: str, start: datetime, end: datetime) -> pd.DataFrame:
    df = pd.read_parquet(path)
    if "datetime" in df.columns:
        df = df.set_index("datetime")
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    df = df.sort_index()
    mask = (df.index >= start) & (df.index <= end)
    out = df.loc[mask, ["open", "high", "low", "close", "volume"]].copy()
    return out


def aggregate_5m(df_1m: pd.DataFrame) -> pd.DataFrame:
    ohlc = df_1m.resample("5min", label="right", closed="right").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    )
    return ohlc.dropna(subset=["close"])


def aggregate_daily(df_5m_ny_session: pd.DataFrame) -> pd.DataFrame:
    """Use the last 5m close within each session as the daily close.

    We filter to NY session bars first (in caller), then take the last bar
    per trading date. This avoids look-ahead: the daily close for date T
    is fully determined by bars with ts <= 21:00 UTC on T.
    """
    df = df_5m_ny_session.copy()
    df["trading_date"] = df.index.date
    daily = df.groupby("trading_date").agg(
        close=("close", "last"),
        session_end_ts=("close", lambda s: s.index[-1]),
    )
    return daily


def filter_session(df: pd.DataFrame, start_hm: str, end_hm: str) -> pd.DataFrame:
    sh, sm = [int(x) for x in start_hm.split(":")]
    eh, em = [int(x) for x in end_hm.split(":")]
    mask = df.index.map(
        lambda ts: (ts.hour > sh or (ts.hour == sh and ts.minute >= sm))
        and (ts.hour < eh or (ts.hour == eh and ts.minute <= em))
    )
    return df.loc[mask]


def align_pair(df_y: pd.DataFrame, df_x: pd.DataFrame) -> pd.DataFrame:
    joined = df_y[["close", "open"]].rename(columns={"close": "close_y", "open": "open_y"}).join(
        df_x[["close", "open"]].rename(columns={"close": "close_x", "open": "open_x"}),
        how="inner",
    )
    return joined.dropna()


def _clean(y: np.ndarray, x: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    mask = np.isfinite(y) & np.isfinite(x)
    return y[mask], x[mask]


def compute_daily_regime(
    daily_y: pd.DataFrame,
    daily_x: pd.DataFrame,
    cfg: SmokeConfigV2,
) -> Dict[Any, Dict[str, Any]]:
    """For each trading_date T, compute EG test on prior `daily_coint_window`
    daily closes (strictly before T, no look-ahead).

    Returns {trading_date: {"is_coint": bool, "p_value": float|None,
                            "window_n": int, "computed": bool}}
    """
    # Align daily series on common trading_date index.
    joined = daily_y[["close"]].rename(columns={"close": "close_y"}).join(
        daily_x[["close"]].rename(columns={"close": "close_x"}),
        how="inner",
    ).dropna().sort_index()

    log_y = np.log(joined["close_y"].to_numpy(dtype=float))
    log_x = np.log(joined["close_x"].to_numpy(dtype=float))
    dates = list(joined.index)

    regime: Dict[Any, Dict[str, Any]] = {}
    W = cfg.daily_coint_window
    for i, date in enumerate(dates):
        # Window = [i-W, i-1] strictly prior, require full window.
        if i < W:
            regime[date] = {
                "is_coint": False,
                "p_value": None,
                "window_n": i,
                "computed": False,
            }
            continue
        y_win = log_y[i - W : i]  # strictly prior to i (no look-ahead)
        x_win = log_x[i - W : i]
        y_c, x_c = _clean(y_win, x_win)
        is_coint = False
        p_value: Optional[float] = None
        if len(y_c) >= W - 5:
            try:
                is_coint, p_value, _ = engle_granger_test(
                    y_c, x_c, alpha=cfg.daily_coint_alpha, max_lag=1
                )
            except Exception as e:
                logger.warning(f"EG test failed on {date}: {e}")
                is_coint = False
                p_value = None
        regime[date] = {
            "is_coint": bool(is_coint),
            "p_value": float(p_value) if p_value is not None else None,
            "window_n": W,
            "computed": True,
        }
    return regime


def compute_signals(joined: pd.DataFrame, cfg: SmokeConfigV2) -> pd.DataFrame:
    log_y = np.log(joined["close_y"].to_numpy(dtype=float))
    log_x = np.log(joined["close_x"].to_numpy(dtype=float))
    beta = rolling_beta(log_y, log_x, cfg.beta_window)
    spread = compute_spread(log_y, log_x, beta)
    z = rolling_zscore(spread, cfg.z_window)
    sig = joined.copy()
    sig["log_y"] = log_y
    sig["log_x"] = log_x
    sig["beta"] = beta
    sig["spread"] = spread
    sig["z"] = z
    return sig


def run_smoke_v2(cfg: SmokeConfigV2) -> Dict[str, Any]:
    start_dt = datetime.fromisoformat(cfg.start_date).replace(tzinfo=timezone.utc)
    end_dt = datetime.fromisoformat(cfg.end_date).replace(
        tzinfo=timezone.utc
    ) + timedelta(days=1)
    load_start = start_dt - timedelta(days=cfg.daily_lookback_days)

    spy = load_1m(str(REPO_ROOT / cfg.spy_path), load_start, end_dt)
    qqq = load_1m(str(REPO_ROOT / cfg.qqq_path), load_start, end_dt)
    logger.info(f"SPY 1m bars: {len(spy)}, QQQ 1m bars: {len(qqq)}")

    spy_5m = aggregate_5m(spy)
    qqq_5m = aggregate_5m(qqq)
    spy_5m = filter_session(spy_5m, cfg.session_start_utc, cfg.session_end_utc)
    qqq_5m = filter_session(qqq_5m, cfg.session_start_utc, cfg.session_end_utc)

    spy_daily = aggregate_daily(spy_5m)
    qqq_daily = aggregate_daily(qqq_5m)
    logger.info(
        f"Daily closes: SPY={len(spy_daily)}, QQQ={len(qqq_daily)} "
        f"(need ≥ {cfg.daily_coint_window} prior to smoke start)"
    )

    regime = compute_daily_regime(spy_daily, qqq_daily, cfg)

    joined = align_pair(spy_5m, qqq_5m)
    logger.info(f"Joined 5m bars (all loaded): {len(joined)}")

    sig = compute_signals(joined, cfg)
    session_mask = (sig.index >= start_dt) & (sig.index <= end_dt)
    sig_session = sig.loc[session_mask].copy()
    logger.info(f"Session 5m bars (smoke window): {len(sig_session)}")

    # Annotate each 5m bar with daily regime status.
    def _regime_for_ts(ts: pd.Timestamp) -> Tuple[bool, Optional[float]]:
        d = ts.date()
        if d not in regime:
            return False, None
        r = regime[d]
        return bool(r["is_coint"]), r["p_value"]

    sig_session["daily_coint_ok"] = [
        _regime_for_ts(ts)[0] for ts in sig_session.index
    ]
    sig_session["daily_coint_pvalue"] = [
        _regime_for_ts(ts)[1] for ts in sig_session.index
    ]

    # Count per-trading-day regime state in smoke window.
    smoke_dates = sorted({ts.date() for ts in sig_session.index})
    regime_trace = {
        str(d): {
            "is_coint": regime.get(d, {}).get("is_coint", False),
            "p_value": regime.get(d, {}).get("p_value"),
            "computed": regime.get(d, {}).get("computed", False),
            "session_bars": int((sig_session.index.date == d).sum()),
        }
        for d in smoke_dates
    }
    daily_coint_pass_days = sum(
        1 for d in smoke_dates if regime.get(d, {}).get("is_coint", False)
    )
    logger.info(
        f"Daily coint regime in smoke window: {daily_coint_pass_days}/{len(smoke_dates)} days ON"
    )

    tracker = PairSpreadTracker(
        entry_z=cfg.entry_z,
        exit_z=cfg.exit_z,
        blowout_z=cfg.blowout_z,
        lockout_bars=cfg.lockout_bars,
        require_cointegration=False,  # gate is at daily level externally
    )

    trades: List[PairTrade] = []
    open_trade: Optional[PairTrade] = None
    open_bars_held = 0
    pair_counter = 0
    bars_skipped_daily_gate = 0

    z_finite_bars = int(np.isfinite(sig_session["z"]).sum())

    bars_iter = list(sig_session.itertuples(index=True))
    for i in range(len(bars_iter) - 1):
        row = bars_iter[i]
        next_row = bars_iter[i + 1]
        ts = row.Index
        z = float(row.z) if np.isfinite(row.z) else float("nan")
        beta = float(row.beta) if np.isfinite(row.beta) else float("nan")
        daily_ok = bool(row.daily_coint_ok)
        daily_pval = row.daily_coint_pvalue

        # Manage open trade first (exit logic unaffected by daily gate once in trade).
        if open_trade is not None:
            open_bars_held += 1
            cur_y = float(row.close_y)
            cur_x = float(row.close_x)
            pnl_now = (
                open_trade.qty_y * (cur_y - open_trade.entry_price_y)
                + open_trade.qty_x * (cur_x - open_trade.entry_price_x)
            )
            open_trade.peak_pnl_dollars = max(open_trade.peak_pnl_dollars, pnl_now)
            open_trade.mae_pnl_dollars = min(open_trade.mae_pnl_dollars, pnl_now)

            exit_reason = None
            if np.isfinite(z):
                if abs(z) <= cfg.exit_z:
                    exit_reason = "TP_MEAN_REVERSION"
                elif abs(z) >= cfg.blowout_z:
                    exit_reason = "SL_BLOWOUT"
            if exit_reason is None and open_bars_held >= cfg.time_stop_bars:
                exit_reason = "TIME_STOP"

            if exit_reason is not None:
                exit_y = float(next_row.open_y)
                exit_x = float(next_row.open_x)
                pnl_final = (
                    open_trade.qty_y * (exit_y - open_trade.entry_price_y)
                    + open_trade.qty_x * (exit_x - open_trade.entry_price_x)
                )
                open_trade.exit_ts = next_row.Index
                open_trade.exit_price_y = exit_y
                open_trade.exit_price_x = exit_x
                open_trade.exit_reason = exit_reason
                open_trade.exit_z = z
                open_trade.pnl_dollars = pnl_final
                open_trade.bars_held = open_bars_held
                r_unit = cfg.risk_dollars
                open_trade.peak_r = open_trade.peak_pnl_dollars / r_unit
                open_trade.mae_r = open_trade.mae_pnl_dollars / r_unit
                open_trade.realized_r = pnl_final / r_unit
                trades.append(open_trade)
                tracker.notify_trade_closed(ts=next_row.Index, reason=exit_reason)
                open_trade = None
                open_bars_held = 0
                continue

        # No open trade — daily gate check before arming.
        if not daily_ok:
            bars_skipped_daily_gate += 1
            continue

        setup = tracker.on_5m_close(ts=ts, z=z, beta=beta, is_cointegrated=True)
        if setup is None:
            continue

        entry_y = float(next_row.open_y)
        entry_x = float(next_row.open_x)
        stop_per_share = 0.005 * entry_y
        size = pair_sizing(
            risk_dollars=cfg.risk_dollars,
            price_y=entry_y,
            price_x=entry_x,
            beta=max(setup["armed_beta"], 0.1),
            direction=setup["direction"],
            stop_distance_r_dollars=stop_per_share,
        )

        pair_counter += 1
        open_trade = PairTrade(
            pair_id=f"{cfg.label}_{pair_counter:04d}",
            entry_ts=next_row.Index,
            exit_ts=None,
            direction=setup["direction"],
            armed_z=setup["armed_z"],
            armed_beta=setup["armed_beta"],
            entry_price_y=entry_y,
            entry_price_x=entry_x,
            exit_price_y=None,
            exit_price_x=None,
            qty_y=size.qty_y,
            qty_x=size.qty_x,
            exit_reason=None,
            exit_z=None,
            peak_pnl_dollars=0.0,
            mae_pnl_dollars=0.0,
            pnl_dollars=None,
            bars_held=0,
            daily_coint_pvalue=float(daily_pval) if daily_pval is not None else None,
        )
        open_bars_held = 0

    # EOD close any remaining position.
    if open_trade is not None:
        last_row = bars_iter[-1]
        pnl_final = (
            open_trade.qty_y * (float(last_row.close_y) - open_trade.entry_price_y)
            + open_trade.qty_x * (float(last_row.close_x) - open_trade.entry_price_x)
        )
        open_trade.exit_ts = last_row.Index
        open_trade.exit_price_y = float(last_row.close_y)
        open_trade.exit_price_x = float(last_row.close_x)
        open_trade.exit_reason = "EOD"
        open_trade.exit_z = float(last_row.z) if np.isfinite(last_row.z) else None
        open_trade.pnl_dollars = pnl_final
        open_trade.bars_held = open_bars_held
        r_unit = cfg.risk_dollars
        open_trade.peak_r = open_trade.peak_pnl_dollars / r_unit
        open_trade.mae_r = open_trade.mae_pnl_dollars / r_unit
        open_trade.realized_r = pnl_final / r_unit
        trades.append(open_trade)

    out_dir = REPO_ROOT / cfg.output_dir / cfg.label
    out_dir.mkdir(parents=True, exist_ok=True)

    if trades:
        trades_df = pd.DataFrame([asdict(t) for t in trades])
        trades_df.to_parquet(out_dir / "trades.parquet", index=False)
    else:
        pd.DataFrame().to_parquet(out_dir / "trades.parquet", index=False)

    def _summary(ts: List[PairTrade]) -> Dict[str, Any]:
        if not ts:
            return {
                "n": 0, "WR": None, "PF": None, "E[R]_gross": None,
                "total_R": 0.0, "peak_R_p80": None, "mae_R_p20": None,
                "exit_reasons": {}, "mean_reversion_rate": None,
            }
        rs = np.array([t.realized_r for t in ts], dtype=float)
        peaks = np.array([t.peak_r for t in ts], dtype=float)
        maes = np.array([t.mae_r for t in ts], dtype=float)
        wins = rs > 0
        gross_profit = float(rs[wins].sum())
        gross_loss = float(-rs[~wins].sum())
        pf = (gross_profit / gross_loss) if gross_loss > 0 else None
        exit_counts: Dict[str, int] = {}
        for t in ts:
            exit_counts[t.exit_reason] = exit_counts.get(t.exit_reason, 0) + 1
        mean_rev_n = exit_counts.get("TP_MEAN_REVERSION", 0)
        return {
            "n": len(ts),
            "WR": float(wins.mean()),
            "PF": pf,
            "E[R]_gross": float(rs.mean()),
            "total_R": float(rs.sum()),
            "peak_R_p80": float(np.percentile(peaks, 80)),
            "mae_R_p20": float(np.percentile(maes, 20)),
            "exit_reasons": exit_counts,
            "mean_reversion_rate": float(mean_rev_n / len(ts)),
        }

    summary = _summary(trades)

    counts = {
        "run_id": cfg.label,
        "config": asdict(cfg),
        "counts": {
            "bars_1m_loaded_spy": int(len(spy)),
            "bars_1m_loaded_qqq": int(len(qqq)),
            "bars_5m_joined_total": int(len(sig)),
            "bars_5m_session_window": int(len(sig_session)),
            "bars_5m_z_finite": z_finite_bars,
            "bars_skipped_daily_gate": bars_skipped_daily_gate,
            "smoke_trading_days": len(smoke_dates),
            "daily_coint_pass_days": daily_coint_pass_days,
            "setups_emitted": pair_counter,
            "trades_closed": len(trades),
        },
        "summary": summary,
    }

    with open(out_dir / "debug_counts.json", "w") as f:
        json.dump(counts, f, indent=2, default=str)

    with open(out_dir / "daily_coint_trace.json", "w") as f:
        json.dump(regime_trace, f, indent=2, default=str)

    logger.info(f"Wrote {out_dir}/trades.parquet + debug_counts.json + daily_coint_trace.json")
    logger.info(
        f"SUMMARY: n={summary['n']} WR={summary['WR']} E[R]={summary['E[R]_gross']} "
        f"peak_R_p80={summary['peak_R_p80']} mean_rev={summary['mean_reversion_rate']} "
        f"daily_coint_pass={daily_coint_pass_days}/{len(smoke_dates)}"
    )
    return counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2025-11-17")
    parser.add_argument("--end", default="2025-11-21")
    parser.add_argument("--label", default="stat_arb_spy_qqq_v2_smoke_nov_w4")
    args = parser.parse_args()
    cfg = SmokeConfigV2(start_date=args.start, end_date=args.end, label=args.label)
    run_smoke_v2(cfg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
