"""P0.6.4 checkpoint monitor (non-intrusive).

Writes JSONL checkpoints to:
  /app/data/backtest_results/p064_checkpoint.log

Checkpoint cadence:
- every ~10% progress *per scenario* (based on BacktestEngine "Processed X/Y minutes" lines)

Fields:
- scenario
- progress_pct / minutes_done / minutes_total
- current_timestamp (approximate last processed candle timestamp)
- trades_cum (grepped from main log)
- rss_mb (runner RSS)

Notes:
- Does not change any trading parameters.
- `current_timestamp` is derived from the union timeline of SPY/QQQ parquet datetimes.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from pathlib import Path

import pandas as pd


LOG_PATH = Path("/app/data/backtest_results/p064_ablation_6m.log")
OUT_PATH = Path("/app/data/backtest_results/p064_checkpoint.log")

TOTAL_RE = re.compile(r"Processed\s+(\d+)/(\d+)\s+minutes\s+\(([^%]+)%\)")
SCEN_RE = re.compile(r"ABLATION:\s+([a-zA-Z0-9_\-]+)")


def _get_runner_pid() -> int | None:
    try:
        out = subprocess.check_output(["pgrep", "-af", "python -m backtest.ablation_runner"], text=True).strip().splitlines()
        if out:
            return int(out[0].split()[0])
    except Exception:
        return None
    return None


def _get_rss_mb(pid: int | None) -> float | None:
    if not pid:
        return None
    try:
        rss_kb = int(subprocess.check_output(["bash", "-lc", f"ps -o rss= -p {pid} | tr -d ' '"], text=True).strip())
        return round(rss_kb / 1024.0, 1)
    except Exception:
        return None


def _count_trades(log_path: Path) -> int | None:
    try:
        return int(subprocess.check_output(["bash", "-lc", f"grep -c 'Trade closed' {log_path} || true"], text=True).strip() or "0")
    except Exception:
        return None


def _build_timeline(data_dir: Path) -> list[pd.Timestamp]:
    # Union of SPY/QQQ timestamps (should match minutes_total).
    ts = []
    for sym in ["SPY", "QQQ"]:
        p = data_dir / f"{sym}.parquet"
        if p.exists():
            df = pd.read_parquet(p, columns=["datetime"])
            ts.append(pd.to_datetime(df["datetime"], utc=True))
    if not ts:
        return []
    all_ts = pd.concat(ts, ignore_index=True).drop_duplicates().sort_values()
    return list(all_ts)


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Build once (lightweight: ~116k items)
    timeline = _build_timeline(Path("/app/data/historical/1m"))

    state = {
        "current_scenario": None,
        "next_threshold": 10,
        "last_pct": None,
        "last_trades": None,
        "last_log_mtime": None,
        "no_update_seconds": 0,
    }

    # We don't strictly rely on pgrep (command line can differ). Instead, we stop when:
    # - no ablation process is found AND
    # - the log file hasn't been updated for a while.
    STOP_IF_NO_UPDATE_FOR_S = 900

    while True:
        # Track log freshness
        if LOG_PATH.exists():
            mtime = LOG_PATH.stat().st_mtime
            if state["last_log_mtime"] is None:
                state["last_log_mtime"] = mtime
            elif mtime == state["last_log_mtime"]:
                state["no_update_seconds"] += 30
            else:
                state["last_log_mtime"] = mtime
                state["no_update_seconds"] = 0

        # Continue until stop condition above triggers (log stale + no process).

        if not LOG_PATH.exists():
            time.sleep(10)
            continue

        try:
            tail = subprocess.check_output(["tail", "-n", "600", str(LOG_PATH)], text=True, stderr=subprocess.DEVNULL)
        except Exception:
            time.sleep(10)
            continue

        # Scenario detection
        scen = None
        for line in reversed(tail.splitlines()):
            m = SCEN_RE.search(line)
            if m:
                scen = m.group(1)
                break
        if scen and scen != state["current_scenario"]:
            state["current_scenario"] = scen
            state["next_threshold"] = 10
            state["last_pct"] = None

        # Progress detection (use last match)
        prog = None
        for line in reversed(tail.splitlines()):
            m = TOTAL_RE.search(line)
            if m:
                done = int(m.group(1))
                total = int(m.group(2))
                pct = float(m.group(3))
                prog = (done, total, pct)
                break

        if prog:
            done, total, pct = prog

            if state["last_pct"] is not None and pct < state["last_pct"]:
                # scenario changed / restarted
                state["next_threshold"] = 10
            state["last_pct"] = pct

            if pct >= state["next_threshold"]:
                pid = _get_runner_pid()
                trades = _count_trades(LOG_PATH)
                trades_delta = None
                if trades is not None and state["last_trades"] is not None:
                    trades_delta = trades - state["last_trades"]
                state["last_trades"] = trades

                current_ts = None
                if timeline:
                    idx = min(max(done - 1, 0), len(timeline) - 1)
                    current_ts = timeline[idx].isoformat()

                checkpoint = {
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "scenario": state["current_scenario"],
                    "progress_pct": pct,
                    "minutes_done": done,
                    "minutes_total": total,
                    "current_timestamp": current_ts,
                    "trades_cum": trades,
                    "trades_delta": trades_delta,
                    "setups_cum": None,
                    "rss_mb": _get_rss_mb(pid),
                }

                with OUT_PATH.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(checkpoint) + "\n")

                while state["next_threshold"] <= pct:
                    state["next_threshold"] += 10

        time.sleep(30)


if __name__ == "__main__":
    main()
