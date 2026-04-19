"""
Regime Filter — ADX and Choppiness Index for market regime detection.

ADX < 20 = range/no trend, ADX > 25 = trending.
Chop Index > 61.8 = choppy, CI < 38.2 = trending.

Pure-Python implementation (no TA-Lib dependency).
"""
import math
from typing import List
from models.market_data import Candle


def calculate_adx(candles: List[Candle], period: int = 14) -> float:
    """
    Calculate Average Directional Index (ADX) using Wilder's smoothing.

    Args:
        candles: List of Candle objects with .high, .low, .close attributes.
        period: Smoothing period (default 14).

    Returns:
        ADX value (0-100). Returns 0.0 if not enough data (need >= 2*period candles).
    """
    n = len(candles)
    if n < 2 * period:
        return 0.0

    # Step 1: Calculate +DM, -DM, and TR for each bar (starting at index 1)
    plus_dm_list = []
    minus_dm_list = []
    tr_list = []

    for i in range(1, n):
        high = candles[i].high
        low = candles[i].low
        prev_high = candles[i - 1].high
        prev_low = candles[i - 1].low
        prev_close = candles[i - 1].close

        # Directional Movement
        up_move = high - prev_high
        down_move = prev_low - low

        plus_dm = up_move if (up_move > down_move and up_move > 0) else 0.0
        minus_dm = down_move if (down_move > up_move and down_move > 0) else 0.0

        # True Range
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))

        plus_dm_list.append(plus_dm)
        minus_dm_list.append(minus_dm)
        tr_list.append(tr)

    # Step 2: First smoothed values = sum of first `period` values
    smoothed_plus_dm = sum(plus_dm_list[:period])
    smoothed_minus_dm = sum(minus_dm_list[:period])
    smoothed_tr = sum(tr_list[:period])

    # Step 3: Calculate first DX values using Wilder's smoothing
    dx_list = []

    for i in range(period, len(plus_dm_list)):
        if i == period:
            # Use the initial sums for the first +DI/-DI
            pass
        else:
            # Wilder's smoothing: smoothed = prev - (prev / period) + current
            smoothed_plus_dm = smoothed_plus_dm - (smoothed_plus_dm / period) + plus_dm_list[i]
            smoothed_minus_dm = smoothed_minus_dm - (smoothed_minus_dm / period) + minus_dm_list[i]
            smoothed_tr = smoothed_tr - (smoothed_tr / period) + tr_list[i]

        # +DI and -DI
        if smoothed_tr == 0:
            plus_di = 0.0
            minus_di = 0.0
        else:
            plus_di = 100.0 * smoothed_plus_dm / smoothed_tr
            minus_di = 100.0 * smoothed_minus_dm / smoothed_tr

        # DX
        di_sum = plus_di + minus_di
        if di_sum == 0:
            dx = 0.0
        else:
            dx = 100.0 * abs(plus_di - minus_di) / di_sum

        dx_list.append(dx)

    # Step 4: ADX = Wilder's smoothing of DX over `period`
    if len(dx_list) < period:
        return 0.0

    # First ADX = average of first `period` DX values
    adx = sum(dx_list[:period]) / period

    # Subsequent ADX values via Wilder's smoothing
    for i in range(period, len(dx_list)):
        adx = (adx * (period - 1) + dx_list[i]) / period

    return adx


def calculate_chop_index(candles: List[Candle], period: int = 14) -> float:
    """
    Calculate Choppiness Index.

    CI > 61.8 = choppy/ranging market, CI < 38.2 = trending market.

    Formula: 100 * log10(sum(ATR_1, period) / (highest_high - lowest_low)) / log10(period)

    Args:
        candles: List of Candle objects with .high, .low, .close attributes.
        period: Lookback period (default 14).

    Returns:
        Chop Index value (0-100). Returns 50.0 if not enough data (need >= period+1 candles).
    """
    n = len(candles)
    if n < period + 1:
        return 50.0

    # Use the last `period + 1` candles (need period+1 to compute period TR values)
    window = candles[-(period + 1):]

    # Calculate True Range for each bar in the window (starting at index 1)
    atr_sum = 0.0
    highest_high = -math.inf
    lowest_low = math.inf

    for i in range(1, len(window)):
        high = window[i].high
        low = window[i].low
        prev_close = window[i - 1].close

        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        atr_sum += tr

        # Track highest high and lowest low over the period
        if high > highest_high:
            highest_high = high
        if low < lowest_low:
            lowest_low = low

    # Avoid division by zero
    price_range = highest_high - lowest_low
    if price_range <= 0:
        return 50.0

    # Choppiness Index formula
    chop = 100.0 * math.log10(atr_sum / price_range) / math.log10(period)

    # Clamp to 0-100
    return max(0.0, min(100.0, chop))


def calculate_vwap(candles: List[Candle]) -> float:
    """Calculate Volume Weighted Average Price from candle list."""
    cum_tp_vol = 0.0
    cum_vol = 0.0
    for c in candles:
        if c.volume > 0:
            typical_price = (c.high + c.low + c.close) / 3.0
            cum_tp_vol += typical_price * c.volume
            cum_vol += c.volume
    return cum_tp_vol / cum_vol if cum_vol > 0 else 0.0


def calculate_avg_volume(candles: List[Candle], period: int = 20) -> float:
    """Calculate average volume over the last `period` candles."""
    window = candles[-period:] if len(candles) >= period else candles
    volumes = [c.volume for c in window if c.volume > 0]
    return sum(volumes) / len(volumes) if volumes else 0.0
