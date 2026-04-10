"""
Phase 1 — PREUVE TEST: câblage sweep -> custom_detectors -> pattern_type liquidity_sweep
compatible avec setup_engine_v2._ict_has_liquidity_sweep.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from engines.patterns.custom_detectors import detect_custom_patterns
from engines.patterns.ict import ICTPatternEngine
from engines.setup_engine_v2 import _ict_has_liquidity_sweep
from models.market_data import Candle


def _candle(i: int, o: float, h: float, low: float, c: float) -> Candle:
    base = datetime(2025, 11, 3, 14, 30, tzinfo=timezone.utc)
    return Candle(
        symbol="SPY",
        timeframe="5m",
        timestamp=base + timedelta(minutes=5 * i),
        open=o,
        high=h,
        low=low,
        close=c,
        volume=1,
    )


def test_custom_detectors_exposes_liquidity_sweep_key():
    """PREUVE TEST: le dict inclut la clé attendue par le backtest (extend sur .values())."""
    candles = [_candle(i, 100.0, 100.5, 99.5, 100.0) for i in range(20)]
    out = detect_custom_patterns(candles, "5m")
    assert "liquidity_sweep" in out
    assert isinstance(out["liquidity_sweep"], list)


def test_detect_liquidity_sweep_produces_liquidity_sweep_pattern_type():
    """
    Bougies synthétiques: pivot low + pivot high (detect_liquidity_sweep exige les deux),
    puis dernière bougie sweep high + rejet (ict.py ~338-339).
    """
    candles: list[Candle] = []
    for i in range(5):
        candles.append(_candle(i, 100.0, 100.2, 99.8, 100.0))
    candles.append(_candle(5, 99.5, 100.0, 98.0, 99.2))
    for i in range(6, 10):
        candles.append(_candle(i, 99.5, 100.2, 99.0, 99.8))
    candles.append(_candle(10, 100.0, 102.0, 99.5, 100.5))
    for i in range(11, 24):
        candles.append(_candle(i, 100.0, 101.0, 99.5, 100.2))
    candles.append(_candle(24, 101.0, 103.5, 100.0, 100.8))

    engine = ICTPatternEngine()
    sweeps = engine.detect_liquidity_sweep(candles, "5m")
    assert len(sweeps) >= 1
    assert sweeps[0].pattern_type == "liquidity_sweep"
    assert _ict_has_liquidity_sweep(sweeps)

    bundled = detect_custom_patterns(candles, "5m")
    assert any(p.pattern_type == "liquidity_sweep" for p in bundled.get("liquidity_sweep", []))


def test_ict_has_liquidity_sweep_accepts_liquidity_sweep_type():
    """Alignement avec setup_engine (set sweep | liquidity_sweep)."""
    from models.setup import ICTPattern

    p = ICTPattern(
        symbol="SPY",
        timeframe="5m",
        pattern_type="liquidity_sweep",
        direction="bearish",
        price_level=102.0,
        strength=0.7,
        confidence=0.8,
        timestamp=datetime.now(timezone.utc),
    )
    assert _ict_has_liquidity_sweep([p]) is True
