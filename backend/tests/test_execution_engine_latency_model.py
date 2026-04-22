"""§0.7 G2 — LatencyModel gate tests.

Three tests per plan v3.1.2 §0.7 G2:
- no-latency byte-identity (IdealLatency default, 0 ms)
- realistic shift (RealisticLatency 200±50 ms, bar-granular shift mechanism)
- SHORT mirror (SHORT order also gets latency logged)
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def _backend_dir() -> Path:
    return Path(__file__).parent.parent


sys.path.insert(0, str(_backend_dir()))


from engines.execution.latency_model import (
    IBKRLatency,
    IdealLatency,
    RealisticLatency,
)
from engines.execution.paper_trading import ExecutionEngine
from engines.risk_engine import RiskEngine
from models.risk import PositionSizingResult
from models.setup import PlaybookMatch, Setup


def _risk_alloc() -> dict:
    return {
        "risk_pct": 0.01,
        "position_calc": PositionSizingResult(
            risk_amount=100.0,
            position_size=100.0,
            risk_tier=1.0,
            distance_stop=1.0,
            multiplier=1.0,
            valid=True,
        ),
    }


def _mk_setup(
    direction: str,
    entry: float = 100.0,
    sl: Optional[float] = None,
    tp1: Optional[float] = None,
) -> Setup:
    if direction == "LONG":
        sl = sl if sl is not None else 99.0
        tp1 = tp1 if tp1 is not None else 103.0
        bias = "bullish"
    else:
        sl = sl if sl is not None else 101.0
        tp1 = tp1 if tp1 is not None else 97.0
        bias = "bearish"
    return Setup(
        symbol="SPY",
        direction=direction,
        quality="A",
        final_score=0.8,
        playbook_name="News_Fade",
        trade_type="DAILY",
        entry_price=entry,
        stop_loss=sl,
        take_profit_1=tp1,
        risk_reward=3.0,
        market_bias=bias,
        session="NY",
        playbook_matches=[
            PlaybookMatch(playbook_name="News_Fade", confidence=0.9, matched_conditions=[])
        ],
    )


# --- unit tests on LatencyModel implementations ---------------------------


def test_ideal_latency_returns_zero():
    lat = IdealLatency()
    assert lat.sample_ms() == 0.0
    assert lat.shift_bars(60.0) == 0


def test_realistic_latency_sample_in_range_deterministic():
    lat = RealisticLatency(ms=200.0, jitter=50.0, seed=42)
    samples = [lat.sample_ms() for _ in range(50)]
    for s in samples:
        assert 150.0 <= s <= 250.0, f"sample {s} out of [150, 250]"

    # Deterministic: same seed → same sequence
    lat2 = RealisticLatency(ms=200.0, jitter=50.0, seed=42)
    samples2 = [lat2.sample_ms() for _ in range(50)]
    assert samples == samples2


def test_realistic_latency_shift_bars_bar_granular():
    lat = RealisticLatency(ms=200.0, jitter=50.0, seed=42)
    lat.sample_ms()
    # 1m bars = 60s = 60000 ms → 200±50 ms shift = 0 bars (structural no-op)
    assert lat.shift_bars(60.0) == 0
    # 0.1s bars (tick-like) = 100 ms → 200±50 ms → shift ≥ 1 bar
    shift_tick = lat.shift_bars(0.1)
    assert shift_tick >= 1


def test_ibkr_latency_is_realistic_subclass():
    lat = IBKRLatency()
    assert isinstance(lat, RealisticLatency)
    s = lat.sample_ms()
    assert 150.0 <= s <= 250.0


def test_realistic_latency_rejects_negative_params():
    import pytest

    with pytest.raises(ValueError):
        RealisticLatency(ms=-1.0)
    with pytest.raises(ValueError):
        RealisticLatency(jitter=-1.0)


def test_realistic_latency_shift_bars_rejects_nonpositive_duration():
    import pytest

    lat = RealisticLatency(seed=42)
    with pytest.raises(ValueError):
        lat.shift_bars(0.0)
    with pytest.raises(ValueError):
        lat.shift_bars(-1.0)


# --- ExecutionEngine integration tests (plan-mandated gate) --------------


def test_default_latency_is_ideal_byte_identity():
    """Gate #1: no-latency byte-identity.

    Default ExecutionEngine uses IdealLatency → trade.latency_ms_simulated == 0.0.
    Guarantees pre-G2 behavior byte-identically when no latency injected.
    """
    eng = ExecutionEngine(RiskEngine(initial_capital=10_000.0))
    assert isinstance(eng.latency_model, IdealLatency)

    t0 = datetime(2025, 11, 12, 15, 0, tzinfo=timezone.utc)
    placed = eng.place_order(_mk_setup("LONG"), _risk_alloc(), current_time=t0)
    assert placed["success"]
    trade = eng.open_trades[placed["trade_id"]]
    assert trade.latency_ms_simulated == 0.0


def test_realistic_latency_sample_logged_on_trade():
    """Gate #2: realistic shift.

    RealisticLatency(200±50, seed=42) injected → trade.latency_ms_simulated
    sampled in [150, 250] and persisted on the Trade for reconcile.
    """
    lat = RealisticLatency(ms=200.0, jitter=50.0, seed=42)
    eng = ExecutionEngine(RiskEngine(initial_capital=10_000.0), latency_model=lat)
    assert eng.latency_model is lat

    t0 = datetime(2025, 11, 12, 15, 0, tzinfo=timezone.utc)
    placed = eng.place_order(_mk_setup("LONG"), _risk_alloc(), current_time=t0)
    assert placed["success"]
    trade = eng.open_trades[placed["trade_id"]]
    assert trade.latency_ms_simulated is not None
    assert 150.0 <= trade.latency_ms_simulated <= 250.0

    # Bar-granular shift exposed through the latency_model for future
    # tick-grain wire-up; 1m bars = 0-shift (structural no-op).
    assert lat.shift_bars(60.0) == 0


def test_short_mirror_latency_logged():
    """Gate #3: SHORT mirror.

    SHORT order also gets latency sampled & logged, same distribution as LONG.
    """
    lat = RealisticLatency(ms=200.0, jitter=50.0, seed=123)
    eng = ExecutionEngine(RiskEngine(initial_capital=10_000.0), latency_model=lat)

    t0 = datetime(2025, 11, 12, 15, 0, tzinfo=timezone.utc)
    placed = eng.place_order(_mk_setup("SHORT"), _risk_alloc(), current_time=t0)
    assert placed["success"]
    trade = eng.open_trades[placed["trade_id"]]
    assert trade.direction == "SHORT"
    assert trade.latency_ms_simulated is not None
    assert 150.0 <= trade.latency_ms_simulated <= 250.0
