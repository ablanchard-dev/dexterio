"""Unit tests for pressure_confirm — 1m BOS / engulfing helper."""
from __future__ import annotations

from dataclasses import dataclass

from engines.features.pressure_confirm import has_1m_pressure


@dataclass
class B:
    open: float
    high: float
    low: float
    close: float


def _flat(n: int, base: float = 100.0) -> list[B]:
    return [B(base, base + 0.05, base - 0.05, base) for _ in range(n)]


def test_empty_input_no_pressure():
    assert has_1m_pressure([], "bullish") is False


def test_invalid_direction_no_pressure():
    bars = _flat(5)
    assert has_1m_pressure(bars, "sideways") is False


def test_bullish_bos_break():
    # 5 flat @ 100, then close 100.50 > prior high (100.05) → BOS bullish.
    bars = _flat(5) + [B(100.0, 100.6, 99.95, 100.5)]
    assert has_1m_pressure(bars, "bullish", window=12, bos_lookback=5) is True


def test_bearish_bos_break():
    bars = _flat(5) + [B(100.0, 100.05, 99.4, 99.5)]
    assert has_1m_pressure(bars, "bearish", window=12, bos_lookback=5) is True


def test_no_break_no_engulfing_no_pressure():
    bars = _flat(8)
    assert has_1m_pressure(bars, "bullish", window=12, bos_lookback=5) is False
    assert has_1m_pressure(bars, "bearish", window=12, bos_lookback=5) is False


def test_bullish_engulfing_detected():
    # Down bar then full bull engulf — closes above prev open, opens at/below prev close.
    bars = _flat(3) + [
        B(open=100.5, high=100.6, low=99.5, close=99.6),   # down bar
        B(open=99.5,  high=100.8, low=99.4, close=100.7),  # bull engulf
    ]
    # No BOS (close 100.7 may break prior 100.6 — relax bos_lookback to avoid).
    assert has_1m_pressure(bars, "bullish", window=12, bos_lookback=20) is True


def test_bearish_engulfing_detected():
    bars = _flat(3) + [
        B(open=99.5,  high=100.5, low=99.4, close=100.4),  # up bar
        B(open=100.5, high=100.6, low=99.3, close=99.4),   # bear engulf
    ]
    assert has_1m_pressure(bars, "bearish", window=12, bos_lookback=20) is True


def test_window_caps_lookback():
    # Bullish BOS sits 20 bars back, but window=5 → only last 5 inspected.
    breakout = [B(100.0, 100.6, 99.95, 100.5)]
    rest = _flat(20)
    bars = breakout + rest
    assert has_1m_pressure(bars, "bullish", window=5, bos_lookback=4) is False


def test_engulfing_ignores_wrong_direction():
    bars = _flat(3) + [
        B(open=100.5, high=100.6, low=99.5, close=99.6),
        B(open=99.5,  high=100.8, low=99.4, close=100.7),  # bull engulf
    ]
    assert has_1m_pressure(bars, "bearish", window=12, bos_lookback=20) is False
