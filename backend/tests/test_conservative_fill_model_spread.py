"""§0.7 G3 — ConservativeFillModel spread_bps gate tests.

Validates:
- spread_bps stacks adverse on top of extra_slippage_pct per fill.
- LONG exits receive bid (price down); SHORT exits pay ask (price up).
- Default spread_bps = 1.0 bp (SPY/QQQ v1); zero spread reproduces pre-G3 math.
- Param validation rejects negative spread_bps / extra_slippage_pct.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path


def _backend_dir() -> Path:
    return Path(__file__).parent.parent


sys.path.insert(0, str(_backend_dir()))


from engines.execution.fill_model import ConservativeFillModel, IdealFillModel
from models.market_data import Candle
from models.trade import Trade


def _mk_trade(direction: str = "LONG", entry: float = 100.0,
              sl: float = 99.0, tp: float = 103.0) -> Trade:
    if direction == "SHORT":
        sl = 101.0
        tp = 97.0
    return Trade(
        date=datetime(2025, 11, 12, tzinfo=timezone.utc),
        time_entry=datetime(2025, 11, 12, 15, 0, tzinfo=timezone.utc),
        symbol="SPY",
        direction=direction,
        bias_htf="bullish" if direction == "LONG" else "bearish",
        session_profile=1,
        session="NY",
        playbook="test",
        setup_quality="A",
        setup_score=0.8,
        trade_type="DAILY",
        entry_price=entry,
        stop_loss=sl,
        take_profit_1=tp,
        exit_price=entry,
        position_size=100.0,
        risk_amount=100.0,
        risk_pct=0.01,
        pnl_dollars=0.0,
        pnl_pct=0.0,
        r_multiple=0.0,
        outcome="win",
        exit_reason="",
    )


def _mk_bar(ts_minute: int, high: float, low: float,
            open_: float = 100.0, close: float = 100.0) -> Candle:
    return Candle(
        symbol="SPY",
        timeframe="1m",
        timestamp=datetime(2025, 11, 12, 15, ts_minute, tzinfo=timezone.utc),
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=1000.0,
    )


def test_default_spread_bps_is_one():
    fm = ConservativeFillModel()
    assert fm.spread_bps == 1.0


def test_rejects_negative_spread_bps():
    import pytest

    with pytest.raises(ValueError):
        ConservativeFillModel(spread_bps=-0.1)


def test_rejects_negative_extra_slippage_pct():
    import pytest

    with pytest.raises(ValueError):
        ConservativeFillModel(extra_slippage_pct=-0.0001)


def test_long_exit_spread_is_bid_side_adverse():
    """LONG SL hit → sells at bid → price down."""
    fm = ConservativeFillModel(extra_slippage_pct=0.0, spread_bps=10.0)  # 10 bps = 0.10%
    trade = _mk_trade(direction="LONG")
    bar = _mk_bar(0, high=100.5, low=98.5)  # hits SL=99
    next_bar = _mk_bar(1, high=99.5, low=98.8, open_=99.2)

    result = fm.fill_stop(trade, bar, next_bar=next_bar)
    assert result is not None and result.filled
    # Base = next_bar.open = 99.2; adverse = 99.2 * 0.001 = 0.0992 down
    expected = 99.2 * (1.0 - 0.001)
    assert abs(result.fill_price - expected) < 1e-6
    assert result.slippage_adjustment > 0


def test_short_exit_spread_is_ask_side_adverse():
    """SHORT SL hit → buys to cover at ask → price up."""
    fm = ConservativeFillModel(extra_slippage_pct=0.0, spread_bps=10.0)
    trade = _mk_trade(direction="SHORT")
    bar = _mk_bar(0, high=101.5, low=99.5)  # hits SL=101 for SHORT
    next_bar = _mk_bar(1, high=101.8, low=100.5, open_=101.2)

    result = fm.fill_stop(trade, bar, next_bar=next_bar)
    assert result is not None and result.filled
    expected = 101.2 * (1.0 + 0.001)
    assert abs(result.fill_price - expected) < 1e-6
    assert result.slippage_adjustment > 0


def test_spread_stacks_on_extra_slippage():
    """Total adverse = extra_slippage_pct + (spread_bps / 10000)."""
    fm = ConservativeFillModel(extra_slippage_pct=0.0005, spread_bps=2.0)  # 5 bps + 2 bps
    trade = _mk_trade(direction="LONG")
    bar = _mk_bar(0, high=100.5, low=98.5)
    next_bar = _mk_bar(1, high=99.5, low=98.8, open_=99.0)

    result = fm.fill_stop(trade, bar, next_bar=next_bar)
    assert result is not None
    total_pct = 0.0005 + 0.0002  # 0.07%
    expected = 99.0 * (1.0 - total_pct)
    assert abs(result.fill_price - expected) < 1e-6


def test_zero_spread_reproduces_pre_g3_behavior():
    """spread_bps=0 → only extra_slippage_pct applies (byte-identity pre-G3)."""
    pre_g3 = ConservativeFillModel(extra_slippage_pct=0.0005, spread_bps=0.0)
    trade = _mk_trade(direction="LONG")
    bar = _mk_bar(0, high=100.5, low=98.5)
    next_bar = _mk_bar(1, high=99.5, low=98.8, open_=99.0)

    result = pre_g3.fill_stop(trade, bar, next_bar=next_bar)
    expected = 99.0 * (1.0 - 0.0005)
    assert result is not None
    assert abs(result.fill_price - expected) < 1e-6


def test_spread_applies_on_take_profit_fill():
    fm = ConservativeFillModel(extra_slippage_pct=0.0, spread_bps=5.0)
    trade = _mk_trade(direction="LONG", tp=103.0)
    bar = _mk_bar(0, high=103.5, low=100.0)  # hits TP=103
    next_bar = _mk_bar(1, high=103.8, low=102.5, open_=103.1)

    result = fm.fill_take_profit(trade, bar, 103.0, "TP1", next_bar=next_bar)
    assert result is not None
    expected = 103.1 * (1.0 - 0.0005)  # LONG exit adverse down
    assert abs(result.fill_price - expected) < 1e-6


def test_spread_applies_on_market_fill():
    fm = ConservativeFillModel(extra_slippage_pct=0.0, spread_bps=5.0)
    trade = _mk_trade(direction="SHORT")
    bar = _mk_bar(0, high=100.2, low=99.8, close=100.0)
    next_bar = _mk_bar(1, high=100.3, low=99.9, open_=100.1)

    result = fm.fill_market(trade, bar, next_bar=next_bar)
    assert result.filled
    expected = 100.1 * (1.0 + 0.0005)  # SHORT exit buy to cover → adverse up
    assert abs(result.fill_price - expected) < 1e-6


def test_ideal_fill_model_unchanged_by_g3():
    """§0.7 G3 should not touch IdealFillModel behavior."""
    fm = IdealFillModel()
    assert not hasattr(fm, "spread_bps")
    trade = _mk_trade(direction="LONG")
    bar = _mk_bar(0, high=103.5, low=100.0)
    result = fm.fill_take_profit(trade, bar, 103.0, "TP1", next_bar=None)
    assert result is not None
    assert result.fill_price == 103.0
    assert result.slippage_adjustment == 0.0
