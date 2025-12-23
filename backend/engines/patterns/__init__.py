"""Patterns package - Candlestick & ICT"""
from .candlesticks import CandlestickPatternEngine
from .ict import ICTPatternEngine
from .helpers import detect_trend, is_after_uptrend, is_after_downtrend

__all__ = [
    'CandlestickPatternEngine',
    'ICTPatternEngine',
    'detect_trend',
    'is_after_uptrend',
    'is_after_downtrend'
]
