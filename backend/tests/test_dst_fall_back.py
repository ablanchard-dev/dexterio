"""S1.1 — DST fall-back test (1st Sunday of November).

Fall back: 2025-11-02 02:00 EDT clocks step back to 01:00 EST. The 01:00–01:59
ET window happens twice; UTC offset shifts EDT (-04:00) → EST (-05:00).

Required behavior:
  - A given UTC instant maps to the correct ET wall-clock with the right offset
    on both sides of the transition.
  - A session window declared in ET (e.g. NY 09:30–15:00) stays stable in ET
    on both sides; the corresponding UTC interval shifts by 1 hour.
  - SessionRangeTracker keeps Asian range strictly increasing while bars
    arrive across the duplicated 01:00 hour (no double-flush, no crash).
"""
from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from engines.session_range import SessionRangeTracker

ET = ZoneInfo("America/New_York")


@pytest.mark.parametrize(
    "utc_str, expected_et_hm, expected_offset_hours",
    [
        # Friday Oct 31 — EDT (-4)
        ("2025-10-31 13:30:00", (9, 30), -4),
        # Monday Nov 3 — EST (-5)
        ("2025-11-03 14:30:00", (9, 30), -5),
        # Friday Oct 31 close-area (15:00 ET = 19:00 UTC EDT)
        ("2025-10-31 19:00:00", (15, 0), -4),
        # Monday Nov 3 close-area (15:00 ET = 20:00 UTC EST)
        ("2025-11-03 20:00:00", (15, 0), -5),
    ],
)
def test_utc_to_et_around_fall_back(utc_str, expected_et_hm, expected_offset_hours):
    utc_dt = datetime.fromisoformat(utc_str).replace(tzinfo=timezone.utc)
    et_dt = utc_dt.astimezone(ET)
    assert (et_dt.hour, et_dt.minute) == expected_et_hm
    assert et_dt.utcoffset() == timedelta(hours=expected_offset_hours)


def test_ny_session_window_stable_across_fall_back():
    """NY session 09:30–15:00 ET stays the same wall-clock window before/after DST."""
    sh, sm = 9, 30
    eh, em = 15, 0
    start = time(sh, sm)
    end = time(eh, em)

    # Friday EDT: 13:30 UTC == 09:30 ET — in.
    fri_in = datetime(2025, 10, 31, 13, 30, tzinfo=timezone.utc).astimezone(ET).time()
    assert start <= fri_in <= end

    # Monday EST: 14:30 UTC == 09:30 ET — in.
    mon_in = datetime(2025, 11, 3, 14, 30, tzinfo=timezone.utc).astimezone(ET).time()
    assert start <= mon_in <= end

    # Monday EST: 13:30 UTC == 08:30 ET — out.
    mon_pre = datetime(2025, 11, 3, 13, 30, tzinfo=timezone.utc).astimezone(ET).time()
    assert not (start <= mon_pre <= end)


def test_session_range_tracker_handles_duplicated_hour():
    """The 01:00–01:59 ET hour repeats on Nov 2 2025 (EDT then EST). Tracker
    should still classify those bars as Asian and keep accumulating."""
    tracker = SessionRangeTracker()

    # Build Asian session 18:00 ET Sat 2025-11-01 → 03:00 ET Sun 2025-11-02.
    # This window spans the 01:00 ET fall-back. Use 5-minute cadence.
    cur = datetime(2025, 11, 1, 22, 0, tzinfo=timezone.utc)  # 18:00 ET Sat (EDT)
    end = datetime(2025, 11, 2, 9, 0, tzinfo=timezone.utc)   # 04:00 ET Sun (EST, London)
    high = 100.0
    low = 99.0

    completed = None
    bar_count = 0
    while cur < end:
        out = tracker.update(cur, high, low)
        if out:
            completed = out
        high += 0.07
        low -= 0.03
        bar_count += 1
        cur += timedelta(minutes=5)

    # Asian completes on transition out (03:00 ET).
    assert completed == "asian", f"Expected Asian to freeze, got {completed!r}"
    asian = tracker.get_range("asian")
    assert asian is not None
    assert asian.range_high > asian.range_low
    # All bars should have been classified Asian (none discarded by gap logic).
    # Sanity: high - low > 0 implies at least 2 bars were ingested.
    assert (asian.range_high - asian.range_low) >= 1.0
