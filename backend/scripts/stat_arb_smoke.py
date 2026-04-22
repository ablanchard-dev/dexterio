"""Stat arb SPY-QQQ smoke harness (Sprint 3, phase D3').

Standalone smoke: bypasses full ExecutionEngine wire-up to get a verdict
on the core hypothesis before committing to a 2-day engine refactor.

Pipeline:
  1. Load 1m SPY + QQQ bars for [start, end].
  2. Aggregate to 5m closes.
  3. For each 5m bar t >= warmup:
       - rolling_beta_t      (window = beta_window)
       - spread_t = log_y - beta_t*log_x
       - z_t                  (window = z_window over spread)
       - cointegration test  (rolling coint_window, recomputed every coint_refresh_bars)
       - feed PairSpreadTracker
  4. On ARMED setup: simulate a pair trade with z-score-based exits.
     Next-bar-open fills on both legs. Exit when:
       |z| <= exit_z  → TP
       |z| >= blowout_z → SL
       bars_in_trade >= time_stop_bars → TIME_STOP
  5. Write trades.parquet + debug_counts.json.

This harness is intentionally minimal. Dollar PnL uses beta-neutral sizing
(backend/engines/stat_arb/sizing.py). No commissions/slippage in v1 smoke
(matches IdealFillModel) — they are added later once the raw signal is
proven non-null.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from engines.stat_arb.cointegration import engle_granger_test  # noqa: E402
from engines.stat_arb.sizing import pair_sizing  # noqa: E402
from engines.stat_arb.tracker import (  # noqa: E402
    STATE_ARMED_LONG,
    STATE_ARMED_SHORT,
    PairSpreadTracker,
)
from engines.stat_arb.zscore import (  # noqa: E402
    compute_spread,
    rolling_beta,
    rolling_zscore,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("stat_arb_smoke")


@dataclass
class SmokeConfig:
    start_date: str = "2025-11-17"
    end_date: str = "2025-11-21"
    symbol_y: str = "SPY"
    symbol_x: str = "QQQ"
    spy_path: str = "backend/data/market/SPY_1m.parquet"
    qqq_path: str = "backend/data/market/QQQ_1m.parquet"
    session_start_utc: str = "14:30"   # 09:30 ET (winter) ~ 14:30 UTC
    session_end_utc: str = "21:00"     # 16:00 ET (winter) ~ 21:00 UTC
    beta_window: int = 60              # 5m bars (5h)
    z_window: int = 60
    coint_window: int = 200            # 5m bars (~16h)
    coint_refresh_bars: int = 12       # recompute coint every hour
    coint_alpha: float = 0.05
    entry_z: float = 2.0
    exit_z: float = 0.5
    blowout_z: float = 3.0
    time_stop_bars: int = 18           # 1.5h cap
    lockout_bars: int = 6
    risk_dollars: float = 100.0
    # Cointegration gate: strict EG at α=0.05 on 200 intraday bars passes
    # only ~1/60 windows (too restrictive). SPY-QQQ are structurally
    # cointegrated by construction; v1 smoke disables this gate and relies
    # on z-score + rolling beta. Promotion run will re-enable with daily-TF
    # cointegration instead.
    require_cointegration: bool = False
    label: str = "stat_arb_spy_qqq_v1_smoke_nov_w4"
    output_dir: str = "backend/results/labs/mini_week/stat_arb_spy_qqq_v1"


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


def _clean_for_regression(y: np.ndarray, x: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    mask = np.isfinite(y) & np.isfinite(x)
    return y[mask], x[mask]


def compute_signals(joined: pd.DataFrame, cfg: SmokeConfig) -> pd.DataFrame:
    log_y = np.log(joined["close_y"].to_numpy(dtype=float))
    log_x = np.log(joined["close_x"].to_numpy(dtype=float))

    beta = rolling_beta(log_y, log_x, cfg.beta_window)
    spread = compute_spread(log_y, log_x, beta)
    z = rolling_zscore(spread, cfg.z_window)

    is_coint = np.full(len(joined), False, dtype=bool)
    last_check_idx = -10**9
    last_result = False
    for i in range(len(joined)):
        if i < cfg.coint_window:
            continue
        if i - last_check_idx >= cfg.coint_refresh_bars:
            y_win = log_y[i - cfg.coint_window + 1 : i + 1]
            x_win = log_x[i - cfg.coint_window + 1 : i + 1]
            y_clean, x_clean = _clean_for_regression(y_win, x_win)
            if len(y_clean) >= cfg.coint_window - 5:
                try:
                    last_result, _, _ = engle_granger_test(
                        y_clean, x_clean, alpha=cfg.coint_alpha, max_lag=1
                    )
                except Exception:
                    last_result = False
            last_check_idx = i
        is_coint[i] = last_result

    sig = joined.copy()
    sig["log_y"] = log_y
    sig["log_x"] = log_x
    sig["beta"] = beta
    sig["spread"] = spread
    sig["z"] = z
    sig["is_coint"] = is_coint
    return sig


def run_smoke(cfg: SmokeConfig) -> Dict[str, Any]:
    start_dt = datetime.fromisoformat(cfg.start_date).replace(tzinfo=timezone.utc)
    end_dt = datetime.fromisoformat(cfg.end_date).replace(
        tzinfo=timezone.utc
    ) + timedelta(days=1)
    # Pull extra history so cointegration window is filled when session starts.
    # 10 calendar days ≈ 7 trading days (~546 5m session bars) > coint_window 200.
    load_start = start_dt - timedelta(days=10)

    spy = load_1m(str(REPO_ROOT / cfg.spy_path), load_start, end_dt)
    qqq = load_1m(str(REPO_ROOT / cfg.qqq_path), load_start, end_dt)
    logger.info(f"SPY 1m bars: {len(spy)}, QQQ 1m bars: {len(qqq)}")

    spy_5m = aggregate_5m(spy)
    qqq_5m = aggregate_5m(qqq)
    spy_5m = filter_session(spy_5m, cfg.session_start_utc, cfg.session_end_utc)
    qqq_5m = filter_session(qqq_5m, cfg.session_start_utc, cfg.session_end_utc)

    joined = align_pair(spy_5m, qqq_5m)
    logger.info(f"Joined 5m bars: {len(joined)}")

    sig = compute_signals(joined, cfg)

    session_mask = (sig.index >= start_dt) & (sig.index <= end_dt)
    sig_session = sig.loc[session_mask].copy()
    logger.info(f"Session 5m bars (smoke window): {len(sig_session)}")

    tracker = PairSpreadTracker(
        entry_z=cfg.entry_z,
        exit_z=cfg.exit_z,
        blowout_z=cfg.blowout_z,
        lockout_bars=cfg.lockout_bars,
        require_cointegration=cfg.require_cointegration,
    )

    trades: List[PairTrade] = []
    open_trade: Optional[PairTrade] = None
    open_bars_held = 0
    pair_counter = 0

    coint_bars = int(sig_session["is_coint"].sum())
    z_finite_bars = int(np.isfinite(sig_session["z"]).sum())

    bars_iter = list(sig_session.itertuples(index=True))
    for i in range(len(bars_iter) - 1):
        row = bars_iter[i]
        next_row = bars_iter[i + 1]
        ts = row.Index
        z = float(row.z) if np.isfinite(row.z) else float("nan")
        beta = float(row.beta) if np.isfinite(row.beta) else float("nan")
        is_coint = bool(row.is_coint)

        # Manage open trade first.
        if open_trade is not None:
            open_bars_held += 1
            # PnL at this bar close on the leg prices (log-price gives R-space).
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
                # Fill on next bar open.
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
                # R-scaling: define R as stop distance in $ (risk_dollars) so
                # peak_r / mae_r / realized_r speak a common language with
                # other Dexterio playbooks.
                r_unit = cfg.risk_dollars
                open_trade.peak_r = open_trade.peak_pnl_dollars / r_unit
                open_trade.mae_r = open_trade.mae_pnl_dollars / r_unit
                open_trade.realized_r = pnl_final / r_unit
                trades.append(open_trade)
                tracker.notify_trade_closed(ts=next_row.Index, reason=exit_reason)
                open_trade = None
                open_bars_held = 0
                continue  # don't check for new arm on this bar

        # No open trade — ask tracker for a new setup on this bar.
        setup = tracker.on_5m_close(ts=ts, z=z, beta=beta, is_cointegrated=is_coint)
        if setup is None:
            continue

        # Fill on next bar open.
        entry_y = float(next_row.open_y)
        entry_x = float(next_row.open_x)
        # Stop distance in $ for beta-neutral sizing: conservative proxy =
        # |blowout_z - armed_z| * spread_std * exposure_y, but we don't have
        # instantaneous spread_std in $-space. We size via per-share proxy:
        #   stop_per_share_y = entry_y * (blowout_z * sigma_log_spread)
        # With spread in log-space sigma ~ 0.001–0.003 typical intraday.
        # Use: stop_dollars_per_share_y = 0.005 * entry_y as v1 proxy.
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
        )
        open_bars_held = 0

    # End-of-period: close any remaining position at last bar close.
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

    # --- persist ---
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
                "n": 0,
                "WR": None,
                "PF": None,
                "E[R]_gross": None,
                "total_R": 0.0,
                "peak_R_p80": None,
                "mae_R_p20": None,
                "exit_reasons": {},
                "mean_reversion_rate": None,
            }
        rs = np.array([t.realized_r for t in ts], dtype=float)
        peaks = np.array([t.peak_r for t in ts], dtype=float)
        maes = np.array([t.mae_r for t in ts], dtype=float)
        wins = rs > 0
        gross_profit = rs[wins].sum()
        gross_loss = -rs[~wins].sum()
        pf = float(gross_profit / gross_loss) if gross_loss > 0 else None
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
            "bars_5m_cointegrated": coint_bars,
            "setups_emitted": pair_counter,
            "trades_closed": len(trades),
        },
        "summary": summary,
    }

    with open(out_dir / "debug_counts.json", "w") as f:
        json.dump(counts, f, indent=2, default=str)

    logger.info(f"Wrote {out_dir}/trades.parquet and debug_counts.json")
    logger.info(
        f"SUMMARY: n={summary['n']} WR={summary['WR']} E[R]={summary['E[R]_gross']} "
        f"peak_R_p80={summary['peak_R_p80']} mean_rev={summary['mean_reversion_rate']}"
    )
    return counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2025-11-17")
    parser.add_argument("--end", default="2025-11-21")
    parser.add_argument("--label", default="stat_arb_spy_qqq_v1_smoke_nov_w4")
    args = parser.parse_args()

    cfg = SmokeConfig(start_date=args.start, end_date=args.end, label=args.label)
    run_smoke(cfg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
