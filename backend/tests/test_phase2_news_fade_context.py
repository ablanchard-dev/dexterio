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
    matches = ev.evaluate_all_playbooks(
        symbol="SPY",
        market_state=ms_bad,
        ict_patterns=[],
        candle_patterns=[],
        current_time=_ny(10, 0),
        trading_mode="AGGRESSIVE",
    )
    nf = [m for m in matches if m.get("playbook_name") == "News_Fade"]
    assert len(nf) == 0


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


def test_volatility_on_synthetic_intraday_candles():
    """Remplace l’ancien test sur une méthode moteur supprimée : score 1m sur série synthétique."""
    from utils.volatility import volatility_score_from_1m

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
    v = volatility_score_from_1m(candles, window=30)
    assert v > 0


def test_news_fade_yaml_stop_option_a_sl_distance_entry_percent_half():
    """OPTION A : le YAML NF documente le stop ±0,5 % (vérité moteur actuelle)."""
    from pathlib import Path

    from engines.playbook_loader import PLAYBOOKS_PATH, PlaybookLoader

    loader = PlaybookLoader(playbooks_path=Path(PLAYBOOKS_PATH))
    nf = loader.get_playbook_by_name("News_Fade")
    assert nf is not None
    assert nf.sl_distance == "entry_percent_0.5"


def test_news_fade_yaml_phase_c_tp1_min_rr_one_r():
    """PHASE C : candidat paper provisoire — TP1 et min_rr alignés à 1.0R dans le YAML canonique."""
    from pathlib import Path

    from engines.playbook_loader import PLAYBOOKS_PATH, PlaybookLoader

    loader = PlaybookLoader(playbooks_path=Path(PLAYBOOKS_PATH))
    nf = loader.get_playbook_by_name("News_Fade")
    assert nf is not None
    assert nf.tp1_rr == 1.0
    assert nf.min_rr == 1.0


def test_news_fade_stop_executed_as_half_percent_via_setup_engine_v2_path():
    """NF emprunte le même _calculate_price_levels que les autres CORE : ±0,5 % depuis last_price."""
    from engines.setup_engine_v2 import SetupEngineV2

    eng = SetupEngineV2()
    t = datetime(2025, 11, 5, 10, 0, tzinfo=timezone.utc)
    bear = CandlestickPattern(
        family="engulfing",
        name="Bear",
        direction="bearish",
        timeframe="1m",
        timestamp=t,
        strength=0.8,
        body_size=0.5,
        confirmation=True,
    )
    bull = CandlestickPattern(
        family="engulfing",
        name="Bull",
        direction="bullish",
        timeframe="1m",
        timestamp=t,
        strength=0.8,
        body_size=0.5,
        confirmation=True,
    )
    ep = 600.0
    short = eng._calculate_price_levels(
        "QQQ", "SHORT", [bear], [], [], 3.0, 3.0, 5.0, last_price=ep
    )
    assert short[0] is not None
    assert short[0] == ep
    assert abs((short[1] - ep) / ep - 0.005) < 1e-12

    long_lv = eng._calculate_price_levels(
        "QQQ", "LONG", [bull], [], [], 3.0, 3.0, 5.0, last_price=ep
    )
    assert long_lv[0] == ep
    assert abs((ep - long_lv[1]) / ep - 0.005) < 1e-12
