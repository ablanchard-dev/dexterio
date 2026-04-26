"""Unit tests for flag_breakout detector — Plan v4.0 J4.3."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from engines.patterns.flag_breakout import detect_flag_breakout
from models.market_data import Candle


def _make_candle(symbol: str, ts: datetime, o: float, h: float, l: float, c: float,
                 v: int = 100_000, tf: str = "5m") -> Candle:
    return Candle(symbol=symbol, timeframe=tf, timestamp=ts, open=o, high=h, low=l, close=c, volume=v)


def _build_baseline(n_bars: int = 40, base_price: float = 100.0,
                    base_vol: int = 100_000) -> list[Candle]:
    """Build n_bars of low-vol baseline candles establishing ATR ~0.2."""
    candles = []
    t0 = datetime(2025, 11, 17, 14, 30, tzinfo=timezone.utc)
    for i in range(n_bars):
        ts = t0 + timedelta(minutes=5 * i)
        # Tiny oscillation to produce ATR ~0.2
        o = base_price
        c = base_price + (0.05 if i % 2 == 0 else -0.05)
        h = max(o, c) + 0.05
        l = min(o, c) - 0.05
        candles.append(_make_candle("SPY", ts, o, h, l, c, base_vol))
    return candles


def test_flag_breakout_bullish_pattern_fires():
    """Baseline + impulsion +1.0 (5x ATR 0.2) + flag tight + breakout vol spike → bullish pattern."""
    candles = _build_baseline(40)
    last_close = candles[-1].close
    t = candles[-1].timestamp + timedelta(minutes=5)
    # Impulsion : big bullish bar +1.0 (5x ATR 0.2)
    candles.append(_make_candle("SPY", t, last_close, last_close + 1.05,
                                  last_close - 0.05, last_close + 1.0, 200_000))
    # Flag : 4 tight bars (range ~0.2 = 0.2x impulse range 1.10)
    flag_top = last_close + 1.05
    for i in range(4):
        ts_i = t + timedelta(minutes=5 * (i + 1))
        candles.append(_make_candle("SPY", ts_i,
                                     flag_top - 0.10, flag_top, flag_top - 0.20, flag_top - 0.10,
                                     100_000))
    # Breakout : current bar closes above flag_top with high volume
    ts_break = t + timedelta(minutes=5 * 5)
    candles.append(_make_candle("SPY", ts_break,
                                 flag_top - 0.05, flag_top + 0.30,
                                 flag_top - 0.10, flag_top + 0.25,
                                 250_000))  # vol 2.5x avg

    patterns = detect_flag_breakout(candles, "5m", {})
    assert len(patterns) == 1
    p = patterns[0]
    assert p.pattern_type == "flag_breakout"
    assert p.direction == "bullish"
    assert p.details["n_flag_bars"] == 4
    assert p.details["entry"] > flag_top
    assert p.details["sl"] < flag_top  # SL below flag_low
    assert p.details["target_1r"] > p.details["entry"]
    assert p.details["vol_ratio"] > 1.2


def test_flag_breakout_bearish_pattern_fires():
    """Bearish mirror : impulsion down + flag tight + breakdown."""
    candles = _build_baseline(40)
    last_close = candles[-1].close
    t = candles[-1].timestamp + timedelta(minutes=5)
    # Bearish impulsion -1.0
    candles.append(_make_candle("SPY", t, last_close, last_close + 0.05,
                                  last_close - 1.05, last_close - 1.0, 200_000))
    flag_bot = last_close - 1.05
    for i in range(3):
        ts_i = t + timedelta(minutes=5 * (i + 1))
        candles.append(_make_candle("SPY", ts_i,
                                     flag_bot + 0.10, flag_bot + 0.20, flag_bot,
                                     flag_bot + 0.10, 100_000))
    ts_break = t + timedelta(minutes=5 * 4)
    candles.append(_make_candle("SPY", ts_break,
                                 flag_bot + 0.05, flag_bot + 0.10,
                                 flag_bot - 0.30, flag_bot - 0.25,
                                 250_000))

    patterns = detect_flag_breakout(candles, "5m", {})
    assert len(patterns) == 1
    p = patterns[0]
    assert p.direction == "bearish"
    assert p.details["sl"] > p.details["entry"]  # SL above entry for SHORT
    assert p.details["target_1r"] < p.details["entry"]


def test_flag_breakout_no_volume_no_signal():
    """Same setup but breakout volume = 1.0x avg → rejected."""
    candles = _build_baseline(40)
    last_close = candles[-1].close
    t = candles[-1].timestamp + timedelta(minutes=5)
    candles.append(_make_candle("SPY", t, last_close, last_close + 1.05,
                                  last_close - 0.05, last_close + 1.0, 200_000))
    flag_top = last_close + 1.05
    for i in range(3):
        ts_i = t + timedelta(minutes=5 * (i + 1))
        candles.append(_make_candle("SPY", ts_i,
                                     flag_top - 0.10, flag_top, flag_top - 0.20, flag_top - 0.10,
                                     100_000))
    # Breakout but vol = baseline (no spike)
    ts_break = t + timedelta(minutes=5 * 4)
    candles.append(_make_candle("SPY", ts_break,
                                 flag_top - 0.05, flag_top + 0.30,
                                 flag_top - 0.10, flag_top + 0.25,
                                 100_000))  # vol 1x avg → fails 1.2x gate

    patterns = detect_flag_breakout(candles, "5m", {})
    assert len(patterns) == 0


def test_flag_breakout_no_impulsion_no_signal():
    """No impulsion bar (all small bars) → no signal."""
    candles = _build_baseline(50)
    patterns = detect_flag_breakout(candles, "5m", {})
    assert len(patterns) == 0


def test_flag_breakout_flag_too_wide_no_signal():
    """Impulsion + wide flag (range > 1.0x impulse range, post-recal 2026-04-25)
    → rejected. Seuil 1.0 = sous-médiane observée SPY 5m intraday (p50=1.03)."""
    candles = _build_baseline(40)
    last_close = candles[-1].close
    t = candles[-1].timestamp + timedelta(minutes=5)
    # Impulsion 1.0
    candles.append(_make_candle("SPY", t, last_close, last_close + 1.05,
                                  last_close - 0.05, last_close + 1.0, 200_000))
    flag_top = last_close + 1.05
    # Wide flag : range = 1.50 (1.50 / 1.10 impulse range = 1.36 > 1.0 threshold)
    for i in range(3):
        ts_i = t + timedelta(minutes=5 * (i + 1))
        candles.append(_make_candle("SPY", ts_i,
                                     flag_top - 0.50, flag_top, flag_top - 1.50,
                                     flag_top - 0.50, 100_000))
    ts_break = t + timedelta(minutes=5 * 4)
    candles.append(_make_candle("SPY", ts_break,
                                 flag_top - 0.05, flag_top + 0.30,
                                 flag_top - 0.10, flag_top + 0.25,
                                 250_000))

    patterns = detect_flag_breakout(candles, "5m", {})
    assert len(patterns) == 0


def test_flag_breakout_insufficient_bars_returns_empty():
    """Less than min required bars → empty result, no exception."""
    candles = _build_baseline(10)  # need 14+5+2+20 = 41 minimum
    patterns = detect_flag_breakout(candles, "5m", {})
    assert patterns == []
