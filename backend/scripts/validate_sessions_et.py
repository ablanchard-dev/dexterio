"""P0.6.4.1 - Session/time window sanity check.

Prints 10 timestamps demonstrating ET conversion + session classification + time_range check.

Expectation:
- 2025-06-02 13:30 UTC => 09:30 ET => session_norm=NY => within_time_range(09:30-10:00)=True

Uses the same session logic as utils.timeframes.get_session_info.
"""

from __future__ import annotations

from datetime import datetime, timezone

from zoneinfo import ZoneInfo

from utils.timeframes import get_session_info


NY = ZoneInfo("America/New_York")


def within_time_range_et(dt_et: datetime, start_hm: str = "09:30", end_hm: str = "10:00") -> bool:
    sh, sm = map(int, start_hm.split(":"))
    eh, em = map(int, end_hm.split(":"))
    cur = (dt_et.hour, dt_et.minute)
    return (cur >= (sh, sm)) and (cur <= (eh, em))


def main() -> None:
    samples_utc = [
        # The explicit proof point
        datetime(2025, 6, 2, 13, 30, tzinfo=timezone.utc),
        datetime(2025, 6, 2, 13, 45, tzinfo=timezone.utc),
        datetime(2025, 6, 2, 14, 0, tzinfo=timezone.utc),
        # Outside NY open window
        datetime(2025, 6, 2, 12, 59, tzinfo=timezone.utc),
        datetime(2025, 6, 2, 16, 0, tzinfo=timezone.utc),
        # London-ish
        datetime(2025, 6, 2, 7, 0, tzinfo=timezone.utc),
        datetime(2025, 6, 2, 8, 0, tzinfo=timezone.utc),
        # Late day
        datetime(2025, 6, 2, 19, 59, tzinfo=timezone.utc),
        datetime(2025, 6, 2, 20, 1, tzinfo=timezone.utc),
        # Another date
        datetime(2025, 11, 3, 14, 30, tzinfo=timezone.utc),
    ]

    for ts_utc in samples_utc:
        ts_et = ts_utc.astimezone(NY)
        sess = get_session_info(ts_utc)
        session_norm = str(sess.get("name")).upper()
        print(
            {
                "ts_utc": ts_utc.isoformat(),
                "ts_et": ts_et.isoformat(),
                "session_norm": session_norm,
                "within_time_range_0930_1000": within_time_range_et(ts_et),
            }
        )


if __name__ == "__main__":
    main()
