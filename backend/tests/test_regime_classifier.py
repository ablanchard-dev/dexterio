"""Unit tests for backend.engines.regime.classifier (plan §0.7 item #1)."""
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from engines.regime.classifier import (
    RegimeClassifier,
    RegimeContext,
    RegimeLabel,
    classify_day_of_week,
    classify_session,
    classify_trend_daily,
    classify_vol_band,
    classify_vol_band_from_atr,
)

ET = ZoneInfo("America/New_York")
UTC = timezone.utc


# ---- session ----------------------------------------------------------------


def _et(year, month, day, hh, mm) -> datetime:
    return datetime(year, month, day, hh, mm, tzinfo=ET)


class TestSession:
    def test_premarket_0400(self):
        assert classify_session(_et(2025, 11, 17, 4, 0)) == "premarket"

    def test_premarket_just_before_open(self):
        assert classify_session(_et(2025, 11, 17, 9, 29)) == "premarket"

    def test_rth_open_at_0930(self):
        assert classify_session(_et(2025, 11, 17, 9, 30)) == "rth_open"

    def test_rth_mid_1100(self):
        assert classify_session(_et(2025, 11, 17, 11, 0)) == "rth_mid"

    def test_lunch_1215(self):
        assert classify_session(_et(2025, 11, 17, 12, 15)) == "lunch"

    def test_rth_pm_1400(self):
        assert classify_session(_et(2025, 11, 17, 14, 0)) == "rth_pm"

    def test_close_1530(self):
        assert classify_session(_et(2025, 11, 17, 15, 30)) == "close"

    def test_post_1700(self):
        assert classify_session(_et(2025, 11, 17, 17, 0)) == "post"

    def test_off_hours_overnight(self):
        assert classify_session(_et(2025, 11, 17, 2, 30)) == "off_hours"

    def test_utc_input_converted(self):
        # 15:00 UTC on 2025-06-16 = 11:00 ET (DST, EDT = UTC-4) → rth_mid
        ts = datetime(2025, 6, 16, 15, 0, tzinfo=UTC)
        assert classify_session(ts) == "rth_mid"

    def test_naive_input_treated_as_utc(self):
        # Naïve 14:35 UTC → 09:35 ET (EST winter, UTC-5) → rth_open
        ts = datetime(2025, 12, 1, 14, 35)  # naïve, treated as UTC
        assert classify_session(ts) == "rth_open"


# ---- vol band ---------------------------------------------------------------


class TestVolBand:
    def test_low_under_15(self):
        assert classify_vol_band(12.3) == "low"

    def test_fertile_15(self):
        assert classify_vol_band(15.0) == "fertile"

    def test_fertile_18(self):
        assert classify_vol_band(18.5) == "fertile"

    def test_panic_25(self):
        assert classify_vol_band(25.0) == "panic"

    def test_panic_35(self):
        assert classify_vol_band(35.0) == "panic"

    def test_none_returns_none(self):
        assert classify_vol_band(None) is None

    def test_atr_fallback_low(self):
        # 0.5% ratio → low
        assert classify_vol_band_from_atr(2.0, 400.0) == "low"

    def test_atr_fallback_fertile(self):
        # 1.0% ratio → fertile
        assert classify_vol_band_from_atr(4.0, 400.0) == "fertile"

    def test_atr_fallback_panic(self):
        # 2.0% ratio → panic
        assert classify_vol_band_from_atr(8.0, 400.0) == "panic"

    def test_atr_fallback_rejects_zero_price(self):
        with pytest.raises(ValueError):
            classify_vol_band_from_atr(1.0, 0.0)


# ---- trend daily ------------------------------------------------------------


class TestTrendDaily:
    def test_uptrend_slope_pos_price_above_50(self):
        assert classify_trend_daily(
            close_today=500, sma_20=495, sma_50=480, sma_20_slope=+0.001
        ) == "uptrend"

    def test_downtrend_slope_neg_price_below_50(self):
        assert classify_trend_daily(
            close_today=400, sma_20=410, sma_50=430, sma_20_slope=-0.002
        ) == "downtrend"

    def test_range_slope_near_zero(self):
        assert classify_trend_daily(
            close_today=450, sma_20=449, sma_50=445, sma_20_slope=+0.0001
        ) == "range"

    def test_range_slope_up_but_price_below_sma50(self):
        # conflicting signal: slope positive, but close < SMA50 → range
        assert classify_trend_daily(
            close_today=460, sma_20=465, sma_50=470, sma_20_slope=+0.002
        ) == "range"

    def test_range_slope_down_but_price_above_sma50(self):
        assert classify_trend_daily(
            close_today=500, sma_20=490, sma_50=480, sma_20_slope=-0.002
        ) == "range"

    def test_rejects_non_positive_close(self):
        with pytest.raises(ValueError):
            classify_trend_daily(0, 1, 1, 0.0)


# ---- day of week ------------------------------------------------------------


class TestDayOfWeek:
    def test_monday(self):
        assert classify_day_of_week(_et(2025, 11, 17, 10, 0)) == "monday"

    def test_tuesday_is_midweek(self):
        assert classify_day_of_week(_et(2025, 11, 18, 10, 0)) == "midweek"

    def test_wednesday_is_midweek(self):
        assert classify_day_of_week(_et(2025, 11, 19, 10, 0)) == "midweek"

    def test_thursday_is_midweek(self):
        assert classify_day_of_week(_et(2025, 11, 20, 10, 0)) == "midweek"

    def test_friday(self):
        assert classify_day_of_week(_et(2025, 11, 21, 10, 0)) == "friday"

    def test_saturday_is_weekend(self):
        assert classify_day_of_week(_et(2025, 11, 22, 10, 0)) == "weekend"

    def test_sunday_is_weekend(self):
        assert classify_day_of_week(_et(2025, 11, 23, 10, 0)) == "weekend"


# ---- DST transitions --------------------------------------------------------


class TestDst:
    def test_spring_forward_session_stays_anchored_ET(self):
        # 2025 DST start: 09 March, 02:00 ET → 03:00 ET
        # Monday 10 Mar, 11:00 ET (rth_mid) under EDT (UTC-4) = 15:00 UTC
        ts_utc = datetime(2025, 3, 10, 15, 0, tzinfo=UTC)
        assert classify_session(ts_utc) == "rth_mid"

    def test_fall_back_session_stays_anchored_ET(self):
        # 2025 DST end: 02 November, 02:00 ET → 01:00 ET
        # Monday 03 Nov, 11:00 ET (rth_mid) under EST (UTC-5) = 16:00 UTC
        ts_utc = datetime(2025, 11, 3, 16, 0, tzinfo=UTC)
        assert classify_session(ts_utc) == "rth_mid"


# ---- orchestrator -----------------------------------------------------------


class TestOrchestrator:
    def test_full_label_with_vix(self):
        clf = RegimeClassifier()
        ctx = RegimeContext(
            ts=_et(2025, 11, 19, 11, 0),
            vix_close_prior=18.0,
            close=590,
            sma_20=585,
            sma_50=570,
            sma_20_slope=+0.0012,
            news_gravity="none",
        )
        label = clf.classify(ctx)
        assert label == RegimeLabel(
            session="rth_mid",
            vol_band="fertile",
            trend_daily="uptrend",
            news_gravity="none",
            day_of_week="midweek",
        )

    def test_label_falls_back_to_atr_when_vix_missing(self):
        clf = RegimeClassifier()
        ctx = RegimeContext(
            ts=_et(2025, 11, 19, 10, 0),
            vix_close_prior=None,
            atr_14=3.0,
            close=500,  # 0.6% ratio → low
        )
        label = clf.classify(ctx)
        assert label.vol_band == "low"

    def test_label_none_when_no_vol_inputs(self):
        clf = RegimeClassifier()
        ctx = RegimeContext(ts=_et(2025, 11, 19, 10, 0))
        label = clf.classify(ctx)
        assert label.vol_band is None
        assert label.trend_daily is None

    def test_label_tag_roundtrip(self):
        lbl = RegimeLabel(
            session="rth_open",
            vol_band="fertile",
            trend_daily="uptrend",
            news_gravity="cpi",
            day_of_week="midweek",
        )
        assert lbl.as_tag() == "rth_open/fertile/uptrend/cpi/midweek"

    def test_label_tag_handles_none_axes(self):
        lbl = RegimeLabel(
            session="premarket",
            vol_band=None,
            trend_daily=None,
            news_gravity="none",
            day_of_week="monday",
        )
        assert lbl.as_tag() == "premarket/na/na/none/monday"

    def test_label_is_frozen(self):
        lbl = RegimeLabel(
            session="rth_open", vol_band="fertile", trend_daily="uptrend",
            news_gravity="none", day_of_week="midweek",
        )
        with pytest.raises(Exception):
            lbl.session = "close"  # type: ignore[misc]
