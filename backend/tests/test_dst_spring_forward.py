"""S1.1 — DST spring-forward test (2nd Sunday of March).

Spring forward: 2025-03-09 02:00 ET clocks jump to 03:00 ET. The 02:00–02:59
ET window does not exist on that day. UTC offset shifts EST (-05:00) →
EDT (-04:00).

Required behavior:
  - A given UTC instant maps to the correct ET wall-clock with the right offset
    on both sides of the transition.
  - A session window declared in ET (e.g. NY 09:30–15:00) stays stable in ET
    on both sides; the corresponding UTC interval shifts by 1 hour.
  - SessionRangeTracker (which classifies per ET wall-clock) does not crash
    on the gap and assigns Asian-session bars correctly across the boundary.
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
        # Friday before spring-forward — EST (-5)
        ("2025-03-07 14:30:00", (9, 30), -5),
        # Monday after spring-forward — EDT (-4)
        ("2025-03-10 13:30:00", (9, 30), -4),
        # Same Friday, NY-close-area (15:00 ET = 20:00 UTC EST)
        ("2025-03-07 20:00:00", (15, 0), -5),
        # Same Monday, NY-close-area (15:00 ET = 19:00 UTC EDT)
        ("2025-03-10 19:00:00", (15, 0), -4),
    ],
)
def test_utc_to_et_around_spring_forward(utc_str, expected_et_hm, expected_offset_hours):
    utc_dt = datetime.fromisoformat(utc_str).replace(tzinfo=timezone.utc)
    et_dt = utc_dt.astimezone(ET)
    assert (et_dt.hour, et_dt.minute) == expected_et_hm
    assert et_dt.utcoffset() == timedelta(hours=expected_offset_hours)


def test_ny_session_window_stable_across_spring_forward():
    """NY session 09:30–15:00 ET stays the same wall-clock window before/after DST."""
    sh, sm = 9, 30
    eh, em = 15, 0
    start = time(sh, sm)
    end = time(eh, em)

    # Friday EST: 14:30 UTC == 09:30 ET (entry edge) — must be in window.
    fri_in = datetime(2025, 3, 7, 14, 30, tzinfo=timezone.utc).astimezone(ET).time()
    assert start <= fri_in <= end

    # Monday EDT: 13:30 UTC == 09:30 ET (entry edge) — must be in window.
    mon_in = datetime(2025, 3, 10, 13, 30, tzinfo=timezone.utc).astimezone(ET).time()
    assert start <= mon_in <= end

    # Monday EDT: 12:30 UTC == 08:30 ET — must be outside.
    mon_pre = datetime(2025, 3, 10, 12, 30, tzinfo=timezone.utc).astimezone(ET).time()
    assert not (start <= mon_pre <= end)


def test_session_range_tracker_handles_spring_forward_gap():
    """Tracker accumulates Asian-session bars across the spring-forward boundary
    without crashing. The 02:00–02:59 ET hour is missing, so the bar sequence
    is 01:59 EST → 03:00 EDT in wall-clock terms."""
    tracker = SessionRangeTracker()

    # Asian session = 18:00 prev → 03:00 ET. Build it on the night of
    # 2025-03-08 (Saturday) into 2025-03-09 (Sunday). DST flips at 02:00 ET.
    bars = []
    # Stride-3-min cadence, 18:00 ET Sat → 04:00 ET Sun (covers boundary).
    cur = datetime(2025, 3, 8, 23, 0, tzinfo=timezone.utc)  # 18:00 ET Sat (EST)
    end = datetime(2025, 3, 9, 8, 0, tzinfo=timezone.utc)   # 04:00 ET Sun (EDT)
    high = 100.0
    low = 99.0
    while cur < end:
        bars.append((cur, high, low))
        high += 0.10
        low -= 0.05
        cur += timedelta(minutes=3)

    completed = None
    for ts, h, l in bars:
        out = tracker.update(ts, h, l)
        if out:
            completed = out

    # Asian range should be frozen on the transition out of Asian (03:00 ET).
    assert completed == "asian", f"Expected Asian to freeze, got {completed!r}"
    asian = tracker.get_range("asian")
    assert asian is not None
    assert asian.range_high > asian.range_low
