"""
Phase 2 — News_Fade: market_context (day_type, volatility), basic filters, instrumentation.
"""
from __future__ import annotations

from datetime import datetime, timezone
import pytest
from zoneinfo import ZoneInfo

from engines.playbook_loader import PlaybookEvaluator, get_playbook_loader
from engines.setup_engine_v2 import SetupEngineV2
from models.market_data import MarketState, Candle
from models.setup import ICTPattern, CandlestickPattern


def _ny(dt_h: int, dt_m: int = 0) -> datetime:
    return datetime(2025, 11, 5, dt_h, dt_m, tzinfo=ZoneInfo("America/New_York"))


def test_playbook_evaluator_nf_passes_basic_when_day_type_and_vol_ok():
    loader = get_playbook_loader()
    nf = loader.get_playbook_by_name("News_Fade")
    assert nf is not None
    ev = PlaybookEvaluator(loader)
    ev.reset_news_fade_basic_instrumentation()
    ms = {
        "bias": "neutral",
        "current_session": "ny",
        "daily_structure": "range",
        "h4_structure": "range",
        "h1_structure": "range",
        "session_profile": 1,
        "day_type": "range",
        "volatility": 1.5,
    }
    ok, reason = ev._check_basic_filters(nf, "SPY", _ny(10, 0), ms)
    assert ok is True
    assert reason is None


def test_playbook_evaluator_nf_rejects_day_type_mismatch():
    loader = get_playbook_loader()
    nf = loader.get_playbook_by_name("News_Fade")
    ev = PlaybookEvaluator(loader)
    ms = {
        "bias": "neutral",
        "current_session": "ny",
        "daily_structure": "uptrend",
        "h4_structure": "uptrend",
        "h1_structure": "uptrend",
        "session_profile": 1,
        "day_type": "trend",
        "volatility": 2.0,
    }
    ok, reason = ev._check_basic_filters(nf, "SPY", _ny(10, 0), ms)
    assert ok is False
    assert reason == "news_events_day_type_mismatch"


def test_playbook_evaluator_nf_rejects_volatility_insufficient():
    loader = get_playbook_loader()
    nf = loader.get_playbook_by_name("News_Fade")
    ev = PlaybookEvaluator(loader)
    ms = {
        "bias": "neutral",
        "current_session": "ny",
        "daily_structure": "range",
        "h4_structure": "range",
        "h1_structure": "range",
        "session_profile": 1,
        "day_type": "range",
        "volatility": 0.05,
    }
    ok, reason = ev._check_basic_filters(nf, "SPY", _ny(10, 0), ms)
    assert ok is False
    assert reason == "volatility_insufficient"


def test_evaluate_all_playbooks_instruments_news_fade_rejects():
    loader = get_playbook_loader()
    ev = PlaybookEvaluator(loader)
    ev.reset_news_fade_basic_instrumentation()
    ms_bad = {
        "bias": "neutral",
        "current_session": "ny",
        "daily_structure": "uptrend",
        "h4_structure": "uptrend",
        "h1_structure": "uptrend",
        "session_profile": 1,
        "day_type": "trend",
        "volatility": 2.0,
    }
    ev.evaluate_all_playbooks(
        symbol="SPY",
        market_state=ms_bad,
        ict_patterns=[],
        candle_patterns=[],
        current_time=_ny(10, 0),
        trading_mode="AGGRESSIVE",
    )
    inst = ev.get_news_fade_basic_instrumentation()
    assert inst["reject_by_reason"].get("news_events_day_type_mismatch", 0) >= 1
    assert inst["pass_basic_filters"] == 0


def test_generate_setups_market_context_contains_day_type_and_volatility():
    """PREUVE: le dict passé à l'évaluateur inclut day_type et volatility."""
    captured: dict = {}

    def capture_evaluate(symbol, market_state, ict_patterns, candle_patterns, current_time, trading_mode):
        captured.clear()
        captured.update(market_state)
        return []

    engine = SetupEngineV2()
    engine.playbook_evaluator.evaluate_all_playbooks = capture_evaluate  # type: ignore[method-assign]

    ms = MarketState(
        symbol="SPY",
        bias="neutral",
        bias_confidence=0.5,
        session_profile=1,
        session_profile_description="",
        daily_structure="range",
        h4_structure="range",
        h1_structure="range",
        day_type="manipulation_reversal",
        current_session="ny",
        volatility=1.2,
    )
    engine.generate_setups(
        symbol="SPY",
        market_state=ms,
        ict_patterns=[],
        candle_patterns=[],
        liquidity_levels=[],
        current_time=datetime.now(timezone.utc),
        trading_mode="AGGRESSIVE",
        last_price=450.0,
    )
    assert "day_type" in captured
    assert captured.get("day_type") == "manipulation_reversal"
    assert "volatility" in captured
    assert captured.get("volatility") == 1.2


def test_compute_ny_rth_session_range_vol_pct():
    from backtest.engine import BacktestEngine
    from models.backtest import BacktestConfig
    from utils.path_resolver import historical_data_path

    cfg = BacktestConfig(
        run_name="phase2_unit",
        symbols=["SPY"],
        data_paths=[str(historical_data_path("1m", "SPY.parquet"))],
        start_date="2025-11-01",
        end_date="2025-11-05",
        output_dir=".",
    )
    eng = BacktestEngine(cfg)
    base = datetime(2025, 11, 5, 14, 30, tzinfo=timezone.utc)
    candles = []
    for i in range(30):
        t = base.replace(minute=30 + i)
        o, h, l, c = 100.0, 100.2, 99.9, 100.1
        if i == 15:
            h, c = 101.0, 100.5
        if i == 20:
            l, c = 98.5, 99.0
        candles.append(
            Candle(symbol="SPY", timeframe="1m", timestamp=t, open=o, high=h, low=l, close=c, volume=1)
        )
    ct = base.replace(hour=19, minute=45)
    v = eng._compute_ny_rth_session_range_vol_pct(candles, ct)
    assert v is not None
    assert v > 0
