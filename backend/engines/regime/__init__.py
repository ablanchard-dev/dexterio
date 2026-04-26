"""Regime classification package — §0.4-bis taxonomy (plan §0.7 item #1).

Exports :
    RegimeLabel                   — 5-axis immutable label (session × vol × trend × news × dow)
    RegimeClassifier              — orchestrator, pure heuristic v1
    classify_session              — ET-aware window lookup
    classify_vol_band             — from VIX close (explicit)
    classify_vol_band_from_atr    — heuristic fallback from ATR/price ratio
    classify_trend_daily          — SMA20 slope + price vs SMA50
    classify_day_of_week          — Mon / mid-week / Fri bucketing
"""
from .classifier import (
    RegimeClassifier,
    RegimeLabel,
    classify_day_of_week,
    classify_session,
    classify_trend_daily,
    classify_vol_band,
    classify_vol_band_from_atr,
)

__all__ = [
    "RegimeClassifier",
    "RegimeLabel",
    "classify_day_of_week",
    "classify_session",
    "classify_trend_daily",
    "classify_vol_band",
    "classify_vol_band_from_atr",
]
