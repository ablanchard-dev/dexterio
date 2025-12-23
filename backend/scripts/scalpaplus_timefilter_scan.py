"""P0.6.4.1 - Timefilter/session scan for SCALP_Aplus_1 (no trading logic).

Goal:
- Evidence that NY session + NY-open time window (09:30-10:00 ET) overlap exists.
- Produces counts comparable to debug_timefilter.

This does NOT run setup detection. It only verifies the wiring: UTC timestamps -> ET -> session classification + time window.

Outputs:
- prints a JSON dict to stdout.
"""

from __future__ import annotations

from datetime import time

import pandas as pd
from zoneinfo import ZoneInfo

from utils.timeframes import get_session_info

NY = ZoneInfo("America/New_York")


def main() -> None:
    # Use SPY as timeline reference (1m index in UTC)
    df = pd.read_parquet("/app/data/historical/1m/SPY.parquet", columns=["open"])
    idx = pd.to_datetime(df.index)

    n_total = len(idx)
    n_pass_session = 0
    n_pass_time_range = 0
    n_pass_both = 0

    start_et = time(9, 30)
    end_et = time(10, 0)

    samples = []

    for ts in idx:
        ts_utc = ts.to_pydatetime()
        sess = get_session_info(ts_utc)
        session_norm = str(sess.get("name", "")).upper()

        ts_et = ts.to_pydatetime().astimezone(NY)
        cur_t = ts_et.timetz().replace(tzinfo=None)

        pass_session = session_norm == "NY"
        pass_time_range = (start_et <= cur_t <= end_et)
        pass_both = pass_session and pass_time_range

        if pass_session:
            n_pass_session += 1
        if pass_time_range:
            n_pass_time_range += 1
        if pass_both:
            n_pass_both += 1
            if len(samples) < 10:
                samples.append(
                    {
                        "ts_utc": ts.isoformat(),
                        "ts_et": ts_et.isoformat(),
                        "session_norm": session_norm,
                        "within_0930_1000": True,
                    }
                )

    out = {
        "N_total_bars_checked": n_total,
        "N_pass_session": n_pass_session,
        "N_pass_time_range": n_pass_time_range,
        "N_pass_both": n_pass_both,
        "samples_pass_both": samples,
    }

    import json

    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
