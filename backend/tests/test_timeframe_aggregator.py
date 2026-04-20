"""P0-7: HTF aggregation boundary tests.

G8: 5m candle[0] = 9:30-9:35 ET, 15m[0] = 9:30-9:45, etc.
G9: 1D candle close correct in EST (Nov-Mar) AND EDT (Mar-Nov).
"""
import pytest
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from models.market_data import Candle
from engines.timeframe_aggregator import TimeframeAggregator

NY = ZoneInfo("America/New_York")


def _make_1m_candle(utc_dt: datetime, symbol: str = "SPY") -> Candle:
    """Create a synthetic 1m candle at the given naive-UTC timestamp."""
    return Candle(
        symbol=symbol,
        timeframe="1m",
        timestamp=utc_dt,  # naive UTC
        open=450.0,
        high=450.5,
        low=449.5,
        close=450.2,
        volume=1000,
    )


def _et_to_utc_naive(year, month, day, hour, minute) -> datetime:
    """Convert ET time to naive UTC datetime."""
    et = datetime(year, month, day, hour, minute, 0, tzinfo=NY)
    utc = et.astimezone(timezone.utc)
    return utc.replace(tzinfo=None)


class TestSubHourlyBoundaries:
    """G8: Sub-hourly TF boundaries."""

    def test_5m_close_at_minute_4(self):
        agg = TimeframeAggregator()
        # Feed 5 bars: minute 30,31,32,33,34 UTC
        for m in range(30, 35):
            c = _make_1m_candle(datetime(2025, 7, 15, 14, m, 0))
            flags = agg.add_1m_candle(c)
        # Minute 34 → 34 % 5 == 4 → should close
        assert flags["is_close_5m"] is True

    def test_5m_not_close_at_minute_3(self):
        agg = TimeframeAggregator()
        for m in range(30, 34):
            c = _make_1m_candle(datetime(2025, 7, 15, 14, m, 0))
            flags = agg.add_1m_candle(c)
        # Minute 33 → 33 % 5 == 3 → not close
        assert flags["is_close_5m"] is False

    def test_15m_close_at_minute_14(self):
        agg = TimeframeAggregator()
        for m in range(0, 15):
            c = _make_1m_candle(datetime(2025, 7, 15, 14, m, 0))
            flags = agg.add_1m_candle(c)
        assert flags["is_close_15m"] is True

    def test_1h_close_at_minute_59(self):
        agg = TimeframeAggregator()
        c = _make_1m_candle(datetime(2025, 7, 15, 14, 59, 0))
        flags = agg.add_1m_candle(c)
        assert flags["is_close_1h"] is True


class TestHTFDSTAware:
    """G9: 4H and 1D close times correct across DST."""

    # ──── EDT (summer) ────
    # EDT = UTC-4, so 15:59 ET = 19:59 UTC

    def test_1d_close_edt(self):
        """1D close at 15:59 ET during EDT (July)."""
        agg = TimeframeAggregator()
        utc_ts = _et_to_utc_naive(2025, 7, 15, 15, 59)
        c = _make_1m_candle(utc_ts)
        flags = agg.add_1m_candle(c)
        assert flags["is_close_1d"] is True, f"1D should close at 15:59 ET (EDT), UTC={utc_ts}"

    def test_1d_not_close_edt_1558(self):
        """1D should NOT close at 15:58 ET."""
        agg = TimeframeAggregator()
        utc_ts = _et_to_utc_naive(2025, 7, 15, 15, 58)
        c = _make_1m_candle(utc_ts)
        flags = agg.add_1m_candle(c)
        assert flags["is_close_1d"] is False

    # ──── EST (winter) ────
    # EST = UTC-5, so 15:59 ET = 20:59 UTC

    def test_1d_close_est(self):
        """1D close at 15:59 ET during EST (January)."""
        agg = TimeframeAggregator()
        utc_ts = _et_to_utc_naive(2025, 1, 15, 15, 59)
        c = _make_1m_candle(utc_ts)
        flags = agg.add_1m_candle(c)
        assert flags["is_close_1d"] is True, f"1D should close at 15:59 ET (EST), UTC={utc_ts}"

    def test_1d_old_bug_est_hour19(self):
        """The OLD bug: hour==19 UTC closes 1D — now it should NOT (in EST, 19:59 UTC = 14:59 ET)."""
        agg = TimeframeAggregator()
        # 19:59 UTC in EST (Jan) = 14:59 ET — NOT market close
        utc_ts = datetime(2025, 1, 15, 19, 59, 0)
        c = _make_1m_candle(utc_ts)
        flags = agg.add_1m_candle(c)
        assert flags["is_close_1d"] is False, (
            "19:59 UTC in EST = 14:59 ET — should NOT be 1D close"
        )

    # ──── 4H boundaries ────

    def test_4h_bar1_close_edt(self):
        """4H bar 1 closes at 13:29 ET during EDT (July)."""
        agg = TimeframeAggregator()
        utc_ts = _et_to_utc_naive(2025, 7, 15, 13, 29)
        c = _make_1m_candle(utc_ts)
        flags = agg.add_1m_candle(c)
        assert flags["is_close_4h"] is True, f"4H bar1 should close at 13:29 ET, UTC={utc_ts}"

    def test_4h_bar2_close_edt(self):
        """4H bar 2 closes at 15:59 ET during EDT (July)."""
        agg = TimeframeAggregator()
        utc_ts = _et_to_utc_naive(2025, 7, 15, 15, 59)
        c = _make_1m_candle(utc_ts)
        flags = agg.add_1m_candle(c)
        assert flags["is_close_4h"] is True, f"4H bar2 should close at 15:59 ET, UTC={utc_ts}"

    def test_4h_bar1_close_est(self):
        """4H bar 1 closes at 13:29 ET during EST (January)."""
        agg = TimeframeAggregator()
        utc_ts = _et_to_utc_naive(2025, 1, 15, 13, 29)
        c = _make_1m_candle(utc_ts)
        flags = agg.add_1m_candle(c)
        assert flags["is_close_4h"] is True, f"4H bar1 should close at 13:29 ET (EST), UTC={utc_ts}"

    def test_4h_not_close_at_random_time(self):
        """4H should NOT close at 11:00 ET."""
        agg = TimeframeAggregator()
        utc_ts = _et_to_utc_naive(2025, 7, 15, 11, 0)
        c = _make_1m_candle(utc_ts)
        flags = agg.add_1m_candle(c)
        assert flags["is_close_4h"] is False

    def test_4h_old_bug_hour13_utc(self):
        """OLD bug: hour==13 minute==59 UTC was flagged as 4H close.
        In EST, 13:59 UTC = 8:59 ET = pre-market, NOT a 4H boundary."""
        agg = TimeframeAggregator()
        utc_ts = datetime(2025, 1, 15, 13, 59, 0)
        c = _make_1m_candle(utc_ts)
        flags = agg.add_1m_candle(c)
        # 13:59 UTC in EST = 8:59 ET → pre-market → NOT a 4H close
        assert flags["is_close_4h"] is False, (
            "13:59 UTC in EST = 8:59 ET pre-market — should NOT be 4H close"
        )


class TestFloorTimestamp:
    """Verify _floor_timestamp produces correct bar starts."""

    def test_floor_5m(self):
        agg = TimeframeAggregator()
        ts = datetime(2025, 7, 15, 14, 33, 45)
        floored = agg._floor_timestamp(ts, "5m")
        assert floored == datetime(2025, 7, 15, 14, 30, 0)

    def test_floor_15m(self):
        agg = TimeframeAggregator()
        ts = datetime(2025, 7, 15, 14, 47, 0)
        floored = agg._floor_timestamp(ts, "15m")
        assert floored == datetime(2025, 7, 15, 14, 45, 0)

    def test_floor_4h_bar1_edt(self):
        """4H bar 1 floor = 9:30 ET in EDT (July)."""
        agg = TimeframeAggregator()
        # 11:00 ET in EDT = 15:00 UTC → should floor to 9:30 ET = 13:30 UTC
        utc_ts = _et_to_utc_naive(2025, 7, 15, 11, 0)
        floored = agg._floor_timestamp(utc_ts, "4h")
        expected = _et_to_utc_naive(2025, 7, 15, 9, 30)
        assert floored == expected, f"4H bar1 floor should be 9:30 ET, got {floored} (expected {expected})"

    def test_floor_4h_bar2_edt(self):
        """4H bar 2 floor = 13:30 ET in EDT (July)."""
        agg = TimeframeAggregator()
        # 14:00 ET in EDT = 18:00 UTC → should floor to 13:30 ET = 17:30 UTC
        utc_ts = _et_to_utc_naive(2025, 7, 15, 14, 0)
        floored = agg._floor_timestamp(utc_ts, "4h")
        expected = _et_to_utc_naive(2025, 7, 15, 13, 30)
        assert floored == expected

    def test_floor_1d_edt(self):
        """1D floor = 9:30 ET."""
        agg = TimeframeAggregator()
        utc_ts = _et_to_utc_naive(2025, 7, 15, 14, 0)
        floored = agg._floor_timestamp(utc_ts, "1d")
        expected = _et_to_utc_naive(2025, 7, 15, 9, 30)
        assert floored == expected

    def test_floor_4h_bar1_est(self):
        """4H bar 1 floor = 9:30 ET in EST (January)."""
        agg = TimeframeAggregator()
        utc_ts = _et_to_utc_naive(2025, 1, 15, 11, 0)
        floored = agg._floor_timestamp(utc_ts, "4h")
        expected = _et_to_utc_naive(2025, 1, 15, 9, 30)
        assert floored == expected
