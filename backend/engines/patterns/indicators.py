"""Indicator-based pattern detectors.

Produces ICTPattern objects for purely mechanical, indicator-driven strategies:
- EMA crossover (9/21 with 50 EMA trend filter)
- VWAP bounce (price touches VWAP + RSI oversold/overbought)
- RSI extreme (RSI(5) < 15 or > 85 mean reversion)
- ORB breakout (opening range high/low break on close)

All detectors return List[ICTPattern] compatible with the existing pipeline.
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional
from models.market_data import Candle
from models.setup import ICTPattern


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ema(values: List[float], period: int) -> List[float]:
    """Compute EMA series. Returns list same length as values (NaN-free from index period-1)."""
    if len(values) < period:
        return [values[0]] * len(values)
    k = 2.0 / (period + 1)
    ema_vals = [0.0] * len(values)
    # Seed with SMA
    ema_vals[period - 1] = sum(values[:period]) / period
    for i in range(period, len(values)):
        ema_vals[i] = values[i] * k + ema_vals[i - 1] * (1 - k)
    # Back-fill early values with SMA seed
    for i in range(period - 1):
        ema_vals[i] = ema_vals[period - 1]
    return ema_vals


def _rsi(closes: List[float], period: int = 14) -> List[float]:
    """Compute RSI series using Wilder smoothing."""
    n = len(closes)
    if n < period + 1:
        return [50.0] * n
    rsi_vals = [50.0] * n
    gains = [0.0] * n
    losses = [0.0] * n
    for i in range(1, n):
        diff = closes[i] - closes[i - 1]
        gains[i] = diff if diff > 0 else 0.0
        losses[i] = -diff if diff < 0 else 0.0
    avg_gain = sum(gains[1:period + 1]) / period
    avg_loss = sum(losses[1:period + 1]) / period
    if avg_loss == 0:
        rsi_vals[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi_vals[period] = 100 - 100 / (1 + rs)
    for i in range(period + 1, n):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            rsi_vals[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi_vals[i] = 100 - 100 / (1 + rs)
    return rsi_vals


def _vwap(candles: List[Candle]) -> List[float]:
    """Compute intraday VWAP (resets each day). Returns list same length as candles."""
    n = len(candles)
    vwap_vals = [0.0] * n
    cum_vol = 0.0
    cum_tp_vol = 0.0
    prev_date = None
    for i, c in enumerate(candles):
        cur_date = c.timestamp.date()
        if prev_date is not None and cur_date != prev_date:
            cum_vol = 0.0
            cum_tp_vol = 0.0
        prev_date = cur_date
        tp = (c.high + c.low + c.close) / 3.0
        vol = c.volume if c.volume > 0 else 1.0
        cum_vol += vol
        cum_tp_vol += tp * vol
        vwap_vals[i] = cum_tp_vol / cum_vol if cum_vol > 0 else c.close
    return vwap_vals


# ---------------------------------------------------------------------------
# Detectors
# ---------------------------------------------------------------------------

def detect_ema_crossover(candles: List[Candle], timeframe: str, config: Dict[str, Any]) -> List[ICTPattern]:
    """Detect EMA 9/21 crossover with 50 EMA trend filter.

    Signal: 9 EMA crosses 21 EMA on the LAST candle.
    Trend filter: price must be on same side of 50 EMA.
    SL: recent swing low (bullish) or swing high (bearish) over lookback.
    Body ratio filter: weak-body candles get strength penalty.
    """
    results: List[ICTPattern] = []
    fast_p = int(config.get('fast_period', 9))
    slow_p = int(config.get('slow_period', 21))
    trend_p = int(config.get('trend_period', 50))
    lookback_sl = int(config.get('lookback_sl', 10))

    n = len(candles)
    min_len = max(trend_p, slow_p) + 2
    if n < min_len:
        return results

    closes = [c.close for c in candles]
    ema_fast = _ema(closes, fast_p)
    ema_slow = _ema(closes, slow_p)
    ema_trend = _ema(closes, trend_p)

    last = n - 1
    prev = n - 2
    c = candles[last]

    # Bullish crossover: fast crosses above slow
    if ema_fast[prev] <= ema_slow[prev] and ema_fast[last] > ema_slow[last]:
        if c.close > ema_trend[last]:  # trend filter
            swing_low = min(cn.low for cn in candles[-lookback_sl:])
            # Body ratio filter: strong close in direction
            c_range = c.high - c.low
            c_body = abs(c.close - c.open)
            body_ratio = c_body / c_range if c_range > 0 else 0
            ema_strength = 0.8
            if body_ratio < 0.5:
                ema_strength *= 0.5
            results.append(ICTPattern(
                symbol=c.symbol,
                timeframe=timeframe,
                pattern_type='ema_cross',
                direction='bullish',
                price_level=swing_low,
                details={
                    'ema_fast': round(ema_fast[last], 4),
                    'ema_slow': round(ema_slow[last], 4),
                    'ema_trend': round(ema_trend[last], 4),
                    'close_price': c.close,
                    'body_ratio': round(body_ratio, 4),
                },
                strength=ema_strength,
                confidence=0.7,
            ))

    # Bearish crossover: fast crosses below slow
    if ema_fast[prev] >= ema_slow[prev] and ema_fast[last] < ema_slow[last]:
        if c.close < ema_trend[last]:
            swing_high = max(cn.high for cn in candles[-lookback_sl:])
            # Body ratio filter: strong close in direction
            c_range = c.high - c.low
            c_body = abs(c.close - c.open)
            body_ratio = c_body / c_range if c_range > 0 else 0
            ema_strength = 0.8
            if body_ratio < 0.5:
                ema_strength *= 0.5
            results.append(ICTPattern(
                symbol=c.symbol,
                timeframe=timeframe,
                pattern_type='ema_cross',
                direction='bearish',
                price_level=swing_high,
                details={
                    'ema_fast': round(ema_fast[last], 4),
                    'ema_slow': round(ema_slow[last], 4),
                    'ema_trend': round(ema_trend[last], 4),
                    'close_price': c.close,
                    'body_ratio': round(body_ratio, 4),
                },
                strength=ema_strength,
                confidence=0.7,
            ))

    return results


def detect_vwap_bounce(candles: List[Candle], timeframe: str, config: Dict[str, Any]) -> List[ICTPattern]:
    """Detect VWAP bounce: price touches VWAP and reverses with RSI confirmation.

    Bullish: price was below VWAP, current candle closes above VWAP, RSI < threshold.
    Bearish: price was above VWAP, current candle closes below VWAP, RSI > threshold.
    """
    results: List[ICTPattern] = []
    rsi_period = int(config.get('rsi_period', 7))
    rsi_oversold = float(config.get('rsi_oversold', 35))
    rsi_overbought = float(config.get('rsi_overbought', 65))
    touch_tolerance = float(config.get('touch_tolerance', 0.0005))  # 0.05% from VWAP

    n = len(candles)
    if n < max(rsi_period + 2, 20):
        return results

    closes = [c.close for c in candles]
    vwap_vals = _vwap(candles)
    rsi_vals = _rsi(closes, rsi_period)

    last = n - 1
    c = candles[last]
    vwap = vwap_vals[last]
    rsi = rsi_vals[last]

    if vwap <= 0:
        return results

    dist_pct = abs(c.close - vwap) / vwap

    # Bullish VWAP bounce: price near/touching VWAP from below, RSI oversold
    if dist_pct <= touch_tolerance and rsi < rsi_oversold:
        # Confirm: previous candle was below VWAP
        if candles[last - 1].close < vwap_vals[last - 1]:
            sl_level = min(cn.low for cn in candles[-10:])
            results.append(ICTPattern(
                symbol=c.symbol,
                timeframe=timeframe,
                pattern_type='vwap_bounce',
                direction='bullish',
                price_level=sl_level,
                details={
                    'vwap': round(vwap, 4),
                    'rsi': round(rsi, 2),
                    'close_price': c.close,
                    'distance_pct': round(dist_pct * 100, 4),
                },
                strength=0.8,
                confidence=0.7,
            ))

    # Bearish VWAP bounce: price near VWAP from above, RSI overbought
    if dist_pct <= touch_tolerance and rsi > rsi_overbought:
        if candles[last - 1].close > vwap_vals[last - 1]:
            sl_level = max(cn.high for cn in candles[-10:])
            results.append(ICTPattern(
                symbol=c.symbol,
                timeframe=timeframe,
                pattern_type='vwap_bounce',
                direction='bearish',
                price_level=sl_level,
                details={
                    'vwap': round(vwap, 4),
                    'rsi': round(rsi, 2),
                    'close_price': c.close,
                    'distance_pct': round(dist_pct * 100, 4),
                },
                strength=0.8,
                confidence=0.7,
            ))

    return results


def detect_rsi_extreme(candles: List[Candle], timeframe: str, config: Dict[str, Any]) -> List[ICTPattern]:
    """Detect RSI(5) extreme mean reversion signal.

    Bullish: RSI(5) < 15 -> price likely to bounce.
    Bearish: RSI(5) > 85 -> price likely to drop.
    SL: recent swing low/high. TP: return to 20 EMA (handled by playbook).
    """
    results: List[ICTPattern] = []
    rsi_period = int(config.get('rsi_period', 5))
    rsi_buy = float(config.get('rsi_buy_threshold', 15))
    rsi_sell = float(config.get('rsi_sell_threshold', 85))
    lookback_sl = int(config.get('lookback_sl', 10))

    n = len(candles)
    if n < rsi_period + 2:
        return results

    closes = [c.close for c in candles]
    rsi_vals = _rsi(closes, rsi_period)

    last = n - 1
    c = candles[last]
    rsi = rsi_vals[last]

    if rsi < rsi_buy:
        swing_low = min(cn.low for cn in candles[-lookback_sl:])
        results.append(ICTPattern(
            symbol=c.symbol,
            timeframe=timeframe,
            pattern_type='rsi_extreme',
            direction='bullish',
            price_level=swing_low,
            details={
                'rsi': round(rsi, 2),
                'rsi_period': rsi_period,
                'close_price': c.close,
            },
            strength=min(1.0, (rsi_buy - rsi) / rsi_buy),
            confidence=0.7,
        ))

    if rsi > rsi_sell:
        swing_high = max(cn.high for cn in candles[-lookback_sl:])
        results.append(ICTPattern(
            symbol=c.symbol,
            timeframe=timeframe,
            pattern_type='rsi_extreme',
            direction='bearish',
            price_level=swing_high,
            details={
                'rsi': round(rsi, 2),
                'rsi_period': rsi_period,
                'close_price': c.close,
            },
            strength=min(1.0, (rsi - rsi_sell) / (100 - rsi_sell)),
            confidence=0.7,
        ))

    return results


def detect_orb_breakout(candles: List[Candle], timeframe: str, config: Dict[str, Any]) -> List[ICTPattern]:
    """Detect Opening Range Breakout.

    The opening range is defined as the high/low of the first N minutes after market open (9:30 ET).
    A breakout occurs when a candle closes outside this range.

    This detector is stateless -- it rebuilds the opening range from the candle history
    each time it's called, by finding candles within [09:30, 09:30+range_minutes) of the
    current day.
    """
    results: List[ICTPattern] = []
    range_minutes = int(config.get('range_minutes', 15))

    n = len(candles)
    if n < 5:
        return results

    last = candles[-1]
    ts = last.timestamp

    # Work in ET -- we need to identify 9:30 AM ET
    try:
        from zoneinfo import ZoneInfo
        et = ZoneInfo("America/New_York")
    except Exception:
        return results

    # Convert to ET
    if ts.tzinfo is None:
        from datetime import timezone as _tz
        ts_et = ts.replace(tzinfo=_tz.utc).astimezone(et)
    else:
        ts_et = ts.astimezone(et)

    market_open_hour = 9
    market_open_min = 30
    from datetime import time as _time, timedelta as _td

    open_time_et = ts_et.replace(hour=market_open_hour, minute=market_open_min, second=0, microsecond=0)
    range_end_et = open_time_et + _td(minutes=range_minutes)

    # Only fire after the range has formed
    if ts_et < range_end_et:
        return results

    # Don't fire after 11:30 ET (ORB is a morning strategy)
    cutoff_et = ts_et.replace(hour=11, minute=30, second=0, microsecond=0)
    if ts_et > cutoff_et:
        return results

    # Find candles within the opening range window
    range_candles = []
    for c in candles:
        c_ts = c.timestamp
        if c_ts.tzinfo is None:
            from datetime import timezone as _tz
            c_et = c_ts.replace(tzinfo=_tz.utc).astimezone(et)
        else:
            c_et = c_ts.astimezone(et)
        # Same day check
        if c_et.date() != ts_et.date():
            continue
        if open_time_et <= c_et < range_end_et:
            range_candles.append(c)

    if len(range_candles) < 2:
        return results

    range_high = max(c.high for c in range_candles)
    range_low = min(c.low for c in range_candles)
    range_size = range_high - range_low
    if range_size <= 0:
        return results

    # Collect post-range candles for retest check
    post_range_candles = []
    for c in candles:
        c_ts = c.timestamp
        if c_ts.tzinfo is None:
            from datetime import timezone as _tz
            c_et = c_ts.replace(tzinfo=_tz.utc).astimezone(et)
        else:
            c_et = c_ts.astimezone(et)
        if c_et.date() == ts_et.date() and c_et >= range_end_et and c is not last:
            post_range_candles.append(c)

    # Breakout: last candle closes outside the range
    if last.close > range_high:
        orb_strength = min(1.0, (last.close - range_high) / range_size)
        # Retest check: did any post-range candle pull back to range_high?
        retested = any(c.low <= range_high for c in post_range_candles)
        if not retested:
            orb_strength *= 0.6
        results.append(ICTPattern(
            symbol=last.symbol,
            timeframe=timeframe,
            pattern_type='orb_break',
            direction='bullish',
            price_level=range_low,  # SL = opposite side of range
            details={
                'range_high': range_high,
                'range_low': range_low,
                'range_size': round(range_size, 4),
                'close_price': last.close,
                'range_minutes': range_minutes,
                'breakout_distance': round(last.close - range_high, 4),
                'retested': retested,
            },
            strength=orb_strength,
            confidence=0.75,
        ))

    if last.close < range_low:
        orb_strength = min(1.0, (range_low - last.close) / range_size)
        # Retest check: did any post-range candle pull back to range_low?
        retested = any(c.high >= range_low for c in post_range_candles)
        if not retested:
            orb_strength *= 0.6
        results.append(ICTPattern(
            symbol=last.symbol,
            timeframe=timeframe,
            pattern_type='orb_break',
            direction='bearish',
            price_level=range_high,  # SL = opposite side of range
            details={
                'range_high': range_high,
                'range_low': range_low,
                'range_size': round(range_size, 4),
                'close_price': last.close,
                'range_minutes': range_minutes,
                'breakout_distance': round(range_low - last.close, 4),
                'retested': retested,
            },
            strength=orb_strength,
            confidence=0.75,
        ))

    return results
