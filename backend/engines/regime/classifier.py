"""Regime classifier v1 heuristique — plan §0.7 item #1.

Implements the 5-axis taxonomy §0.4-bis used for :
  - Stage 1/2 per-regime splits in verdicts (no edge "universelle" hiding)
  - Stage 3 cross-regime validation gate (≥3/5 regimes positive)
  - Stage 4 paper-trading awareness (tag live trades for later analysis)

v1 is intentionally heuristic (no learned component, no external feed beyond
what the caller provides) per §9.1 — ML classifiers come AFTER gross-positive
signal is found.

Design : pure functions (no engine/broker dep, no I/O). Caller provides the
inputs (timestamp, VIX close OR ATR ratio, daily OHLC summary, news flag).
Orchestrator `RegimeClassifier.classify(ctx)` returns an immutable `RegimeLabel`.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from typing import Literal, Optional
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")


# ---------- axis 1 : session ---------------------------------------------------

SessionTag = Literal[
    "premarket",  # 04:00 – 09:30 ET
    "rth_open",   # 09:30 – 10:30
    "rth_mid",    # 10:30 – 12:00
    "lunch",      # 12:00 – 13:30
    "rth_pm",     # 13:30 – 15:00
    "close",      # 15:00 – 16:00
    "post",       # 16:00 – 20:00
    "off_hours",  # anything else (overnight / weekend)
]

# (start, end) half-open windows in ET wall-clock
_SESSION_WINDOWS: list[tuple[SessionTag, time, time]] = [
    ("premarket", time(4, 0),  time(9, 30)),
    ("rth_open",  time(9, 30), time(10, 30)),
    ("rth_mid",   time(10, 30), time(12, 0)),
    ("lunch",     time(12, 0), time(13, 30)),
    ("rth_pm",    time(13, 30), time(15, 0)),
    ("close",     time(15, 0), time(16, 0)),
    ("post",      time(16, 0), time(20, 0)),
]


def classify_session(ts: datetime) -> SessionTag:
    """Return the session tag for a given timestamp.

    The timestamp is converted to America/New_York before comparison, so DST
    transitions are handled by ZoneInfo. Naïve datetimes are assumed UTC.
    """
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=ZoneInfo("UTC"))
    t_et = ts.astimezone(ET).time()
    for tag, start, end in _SESSION_WINDOWS:
        if start <= t_et < end:
            return tag
    return "off_hours"


# ---------- axis 2 : vol band --------------------------------------------------

VolBand = Literal["low", "fertile", "panic"]

VIX_LOW_CEIL = 15.0
VIX_FERTILE_CEIL = 25.0


def classify_vol_band(vix_close: Optional[float]) -> Optional[VolBand]:
    """Band the prior-day VIX close per §0.4-bis.

    Returns None if the caller cannot supply a VIX value (e.g. live feed
    before the first daily close) — downstream code must handle None
    explicitly rather than guessing.
    """
    if vix_close is None:
        return None
    if vix_close < VIX_LOW_CEIL:
        return "low"
    if vix_close < VIX_FERTILE_CEIL:
        return "fertile"
    return "panic"


# ATR-ratio fallback — rough mapping calibrated against SPY 2025 distribution.
# Intended for runtime when VIX isn't cheap to fetch (e.g. intraday paper).
# NOT a substitute for the official VIX band in verdicts/backtests.
_ATR_LOW_CEIL = 0.0065      # atr_14 / close < 0.65 % ≈ VIX < 15
_ATR_FERTILE_CEIL = 0.0130  # < 1.30 % ≈ VIX 15-25


def classify_vol_band_from_atr(atr_14: float, close: float) -> VolBand:
    """Heuristic vol band from ATR(14) / close ratio.

    Raises ValueError on non-positive close (caller bug). atr_14=0 returns
    "low" by convention.
    """
    if close <= 0:
        raise ValueError(f"close must be positive, got {close}")
    ratio = atr_14 / close
    if ratio < _ATR_LOW_CEIL:
        return "low"
    if ratio < _ATR_FERTILE_CEIL:
        return "fertile"
    return "panic"


# ---------- axis 3 : trend daily -----------------------------------------------

TrendDaily = Literal["uptrend", "downtrend", "range"]

# |slope| threshold as fraction of price for range classification
_SLOPE_RANGE_EPS = 0.0005  # 0.05 % / day


def classify_trend_daily(
    close_today: float,
    sma_20: float,
    sma_50: float,
    sma_20_slope: float,
) -> TrendDaily:
    """Trend daily per §0.4-bis.

    - uptrend   : SMA20 slope > +ε AND close > SMA50
    - downtrend : SMA20 slope < −ε AND close < SMA50
    - range     : anything else (including "slope up but price below SMA50")

    `sma_20_slope` = (sma_20[today] - sma_20[today-N]) / N, expressed as a
    fraction of close (i.e. normalised so the same ε threshold works across
    price levels). Caller precomputes it from daily data.
    """
    if close_today <= 0:
        raise ValueError(f"close_today must be positive, got {close_today}")
    eps = _SLOPE_RANGE_EPS
    if sma_20_slope > eps and close_today > sma_50:
        return "uptrend"
    if sma_20_slope < -eps and close_today < sma_50:
        return "downtrend"
    return "range"


# ---------- axis 4 : news gravity ----------------------------------------------

NewsGravity = Literal["none", "earnings_day", "fomc", "cpi", "nfp", "other"]


# ---------- axis 5 : day of week -----------------------------------------------

DayOfWeekBucket = Literal["monday", "midweek", "friday", "weekend"]


def classify_day_of_week(ts: datetime) -> DayOfWeekBucket:
    """Bucket the calendar weekday (ET) into the 4 groups used by §0.4-bis."""
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=ZoneInfo("UTC"))
    wd = ts.astimezone(ET).weekday()  # Mon=0, Sun=6
    if wd == 0:
        return "monday"
    if 1 <= wd <= 3:
        return "midweek"
    if wd == 4:
        return "friday"
    return "weekend"


# ---------- orchestrator -------------------------------------------------------


@dataclass(frozen=True)
class RegimeLabel:
    """Immutable 5-axis label for a single decision point (bar or trade)."""
    session: SessionTag
    vol_band: Optional[VolBand]
    trend_daily: Optional[TrendDaily]
    news_gravity: NewsGravity
    day_of_week: DayOfWeekBucket

    def as_tag(self) -> str:
        """Short canonical string, e.g. "rth_open/fertile/uptrend/none/midweek".

        Missing axes render as "na" so splits key cleanly.
        """
        vb = self.vol_band or "na"
        td = self.trend_daily or "na"
        return f"{self.session}/{vb}/{td}/{self.news_gravity}/{self.day_of_week}"


@dataclass
class RegimeContext:
    """Inputs required to classify a single bar.

    Vol and trend inputs are optional — if absent, the corresponding axis is
    None in the label (rather than guessed).
    """
    ts: datetime
    vix_close_prior: Optional[float] = None
    atr_14: Optional[float] = None
    close: Optional[float] = None
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    sma_20_slope: Optional[float] = None
    news_gravity: NewsGravity = "none"


class RegimeClassifier:
    """Stateless orchestrator — wraps the per-axis helpers."""

    def classify(self, ctx: RegimeContext) -> RegimeLabel:
        session = classify_session(ctx.ts)

        if ctx.vix_close_prior is not None:
            vol = classify_vol_band(ctx.vix_close_prior)
        elif ctx.atr_14 is not None and ctx.close is not None:
            vol = classify_vol_band_from_atr(ctx.atr_14, ctx.close)
        else:
            vol = None

        if (
            ctx.close is not None
            and ctx.sma_20 is not None
            and ctx.sma_50 is not None
            and ctx.sma_20_slope is not None
        ):
            trend = classify_trend_daily(ctx.close, ctx.sma_20, ctx.sma_50, ctx.sma_20_slope)
        else:
            trend = None

        dow = classify_day_of_week(ctx.ts)

        return RegimeLabel(
            session=session,
            vol_band=vol,
            trend_daily=trend,
            news_gravity=ctx.news_gravity,
            day_of_week=dow,
        )
