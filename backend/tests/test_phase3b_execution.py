"""Phase 3B — exécution paper/backtest Wave 1 (garde PHASE3B_PLAYBOOKS)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from engines.execution.paper_trading import ExecutionEngine
from engines.execution.phase3b_execution import PHASE3B_PLAYBOOKS, is_phase3b_playbook
from engines.risk_engine import RiskEngine
from models.risk import PositionSizingResult
from models.setup import Setup, PlaybookMatch
from models.trade import Trade
from models.backtest import BacktestConfig
from backtest.engine import BacktestEngine
import pandas as pd
import pytest


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


def _mk_setup_wave1(
    playbook: str,
    trade_type: str,
    entry: float = 100.0,
    sl: float = 99.0,
    tp1: float = 103.0,
    tp2: Optional[float] = None,
) -> Setup:
    return Setup(
        symbol="SPY",
        direction="LONG",
        quality="A",
        final_score=0.8,
        playbook_name=playbook,
        trade_type=trade_type,
        entry_price=entry,
        stop_loss=sl,
        take_profit_1=tp1,
        take_profit_2=tp2,
        risk_reward=3.0,
        market_bias="bullish",
        session="NY",
        playbook_matches=[
            PlaybookMatch(playbook_name=playbook, confidence=0.9, matched_conditions=[])
        ],
    )


def _mk_setup_news_fade_short() -> Setup:
    return Setup(
        symbol="SPY",
        direction="SHORT",
        quality="A",
        final_score=0.8,
        playbook_name="News_Fade",
        trade_type="DAILY",
        entry_price=100.0,
        stop_loss=100.5,
        take_profit_1=98.5,
        risk_reward=3.0,
        market_bias="bearish",
        session="NY",
        playbook_matches=[
            PlaybookMatch(playbook_name="News_Fade", confidence=0.9, matched_conditions=[])
        ],
    )


def test_phase3b_guard_is_frozen_set():
    assert "NY_Open_Reversal" in PHASE3B_PLAYBOOKS
    assert "FVG_Fill_Scalp" not in PHASE3B_PLAYBOOKS
    assert is_phase3b_playbook("Liquidity_Sweep_Scalp")


def test_breakeven_ny_open_reversal_at_1r_not_0_5r():
    risk = RiskEngine(initial_capital=10_000.0)
    risk._max_scalp_minutes = 120.0
    ex = ExecutionEngine(risk)
    t0 = datetime(2025, 11, 12, 15, 0, tzinfo=timezone.utc)
    placed = ex.place_order(_mk_setup_wave1("NY_Open_Reversal", "DAILY"), _risk_alloc(), current_time=t0)
    assert placed["success"]
    tid = placed["trade_id"]
    tr = ex.open_trades[tid]
    assert tr.breakeven_trigger_rr == 1.0
    assert tr.initial_stop_loss == 99.0

    ex.update_open_trades({"SPY": 100.5}, current_time=t0 + timedelta(minutes=1))
    assert tr.stop_loss == 99.0
    assert tr.breakeven_moved is False

    ex.update_open_trades({"SPY": 101.0}, current_time=t0 + timedelta(minutes=2))
    assert tr.breakeven_moved is True
    assert tr.stop_loss == 100.0


def test_breakeven_news_fade_at_1r():
    risk = RiskEngine(initial_capital=10_000.0)
    ex = ExecutionEngine(risk)
    t0 = datetime(2025, 11, 12, 15, 0, tzinfo=timezone.utc)
    placed = ex.place_order(_mk_setup_wave1("News_Fade", "DAILY"), _risk_alloc(), current_time=t0)
    tr = ex.open_trades[placed["trade_id"]]
    assert tr.breakeven_trigger_rr == 1.0
    assert tr.initial_stop_loss == 99.0

    ex.update_open_trades({"SPY": 100.5}, current_time=t0 + timedelta(minutes=1))
    assert tr.breakeven_moved is False
    ex.update_open_trades({"SPY": 101.0}, current_time=t0 + timedelta(minutes=2))
    assert tr.breakeven_moved is True


def test_time_stop_liquidity_sweep_scalp_30_min_not_global_120():
    risk = RiskEngine(initial_capital=10_000.0)
    risk._max_scalp_minutes = 120.0
    ex = ExecutionEngine(risk)
    t0 = datetime(2025, 11, 3, 14, 30, tzinfo=timezone.utc)
    placed = ex.place_order(
        _mk_setup_wave1("Liquidity_Sweep_Scalp", "SCALP"), _risk_alloc(), current_time=t0
    )
    tid = placed["trade_id"]
    tr = ex.open_trades[tid]
    assert tr.max_hold_minutes == 30.0

    events = ex.update_open_trades({"SPY": 100.1}, current_time=t0 + timedelta(minutes=31))
    assert tid not in ex.open_trades
    assert any(e.get("event_type") == "TIME_STOP" for e in events)
    assert any(e.get("max_minutes") == 30.0 for e in events if e.get("event_type") == "TIME_STOP")
    closed = ex.closed_trades[-1]
    assert closed.exit_reason == "time_stop"
    assert closed.duration_minutes <= 30.0


def test_session_end_news_fade_closes_after_window_end():
    risk = RiskEngine(initial_capital=10_000.0)
    ex = ExecutionEngine(risk)
    t_entry = datetime(2025, 6, 15, 18, 30, tzinfo=timezone.utc)
    t_end = datetime(2025, 6, 15, 19, 31, tzinfo=timezone.utc)
    tr = Trade(
        date=t_entry.date(),
        time_entry=t_entry,
        symbol="SPY",
        direction="LONG",
        bias_htf="bullish",
        session_profile=0,
        session="NY",
        playbook="News_Fade",
        setup_quality="A",
        setup_score=0.8,
        trade_type="DAILY",
        entry_price=100.0,
        stop_loss=99.0,
        initial_stop_loss=99.0,
        take_profit_1=103.0,
        exit_price=0.0,
        position_size=10.0,
        risk_amount=10.0,
        risk_pct=0.01,
        pnl_dollars=0.0,
        pnl_pct=0.0,
        r_multiple=0.0,
        outcome="pending",
        exit_reason="",
        confluences={},
        breakeven_trigger_rr=1.0,
        session_window_end_utc=datetime(2025, 6, 15, 19, 30, tzinfo=timezone.utc),
    )
    ex.open_trades[tr.id] = tr
    events = ex.update_open_trades({"SPY": 100.2}, current_time=t_end)
    assert tr.id not in ex.open_trades
    assert any(e.get("event_type") == "SESSION_END" for e in events)
    assert ex.closed_trades[-1].exit_reason == "session_end"


def test_news_fade_tp_evaluated_before_session_end_when_both_conditions_hold():
    """NF seul : au-delà de la borne fenêtre, si le prix touche TP1, TP l'emporte sur session_end."""
    risk = RiskEngine(initial_capital=10_000.0)
    ex = ExecutionEngine(risk)
    t_entry = datetime(2025, 6, 15, 18, 30, tzinfo=timezone.utc)
    t_after = datetime(2025, 6, 15, 19, 31, tzinfo=timezone.utc)
    tr = Trade(
        date=t_entry.date(),
        time_entry=t_entry,
        symbol="SPY",
        direction="LONG",
        bias_htf="bullish",
        session_profile=0,
        session="NY",
        playbook="News_Fade",
        setup_quality="A",
        setup_score=0.8,
        trade_type="DAILY",
        entry_price=100.0,
        stop_loss=99.0,
        initial_stop_loss=99.0,
        take_profit_1=103.0,
        exit_price=0.0,
        position_size=10.0,
        risk_amount=10.0,
        risk_pct=0.01,
        pnl_dollars=0.0,
        pnl_pct=0.0,
        r_multiple=0.0,
        outcome="pending",
        exit_reason="",
        confluences={},
        breakeven_trigger_rr=1.0,
        session_window_end_utc=datetime(2025, 6, 15, 19, 30, tzinfo=timezone.utc),
    )
    ex.open_trades[tr.id] = tr
    events = ex.update_open_trades({"SPY": 103.0}, current_time=t_after)
    assert tr.id not in ex.open_trades
    assert any(e.get("event_type") == "TP1_HIT" for e in events)
    assert ex.closed_trades[-1].exit_reason == "TP1"


def test_ny_open_reversal_session_end_still_before_tp_when_both_conditions_hold():
    """NY inchangé : session_end reste prioritaire sur TP si les deux sont possibles ce tick."""
    risk = RiskEngine(initial_capital=10_000.0)
    ex = ExecutionEngine(risk)
    t_entry = datetime(2025, 6, 15, 18, 30, tzinfo=timezone.utc)
    t_after = datetime(2025, 6, 15, 19, 31, tzinfo=timezone.utc)
    tr = Trade(
        date=t_entry.date(),
        time_entry=t_entry,
        symbol="SPY",
        direction="LONG",
        bias_htf="bullish",
        session_profile=0,
        session="NY",
        playbook="NY_Open_Reversal",
        setup_quality="A",
        setup_score=0.8,
        trade_type="DAILY",
        entry_price=100.0,
        stop_loss=99.0,
        initial_stop_loss=99.0,
        take_profit_1=103.0,
        exit_price=0.0,
        position_size=10.0,
        risk_amount=10.0,
        risk_pct=0.01,
        pnl_dollars=0.0,
        pnl_pct=0.0,
        r_multiple=0.0,
        outcome="pending",
        exit_reason="",
        confluences={},
        breakeven_trigger_rr=1.0,
        session_window_end_utc=datetime(2025, 6, 15, 19, 30, tzinfo=timezone.utc),
    )
    ex.open_trades[tr.id] = tr
    events = ex.update_open_trades({"SPY": 103.0}, current_time=t_after)
    assert tr.id not in ex.open_trades
    assert any(e.get("event_type") == "SESSION_END" for e in events)
    assert ex.closed_trades[-1].exit_reason == "session_end"


def test_ny_tp1_same_tick_skips_breakeven_after_try_take_profits():
    """Régression : après TP1, `continue` évite BE + effets de bord sur le même tick (branche non-NF)."""
    risk = RiskEngine(initial_capital=10_000.0)
    ex = ExecutionEngine(risk)
    t_entry = datetime(2025, 6, 15, 18, 30, tzinfo=timezone.utc)
    t_in_window = datetime(2025, 6, 15, 19, 0, tzinfo=timezone.utc)
    tr = Trade(
        date=t_entry.date(),
        time_entry=t_entry,
        symbol="SPY",
        direction="LONG",
        bias_htf="bullish",
        session_profile=0,
        session="NY",
        playbook="NY_Open_Reversal",
        setup_quality="A",
        setup_score=0.8,
        trade_type="DAILY",
        entry_price=100.0,
        stop_loss=99.0,
        initial_stop_loss=99.0,
        take_profit_1=103.0,
        exit_price=0.0,
        position_size=10.0,
        risk_amount=10.0,
        risk_pct=0.01,
        pnl_dollars=0.0,
        pnl_pct=0.0,
        r_multiple=0.0,
        outcome="pending",
        exit_reason="",
        confluences={},
        breakeven_trigger_rr=1.0,
        session_window_end_utc=datetime(2025, 6, 15, 19, 30, tzinfo=timezone.utc),
    )
    ex.open_trades[tr.id] = tr
    events = ex.update_open_trades({"SPY": 103.0}, current_time=t_in_window)
    assert tr.id not in ex.open_trades
    assert ex.closed_trades[-1].exit_reason == "TP1"
    assert any(e.get("event_type") == "TP1_HIT" for e in events)
    assert not any(e.get("event_type") == "BREAKEVEN_MOVED" for e in events)


def test_news_fade_initial_stop_preserved_after_breakeven_and_r_on_close():
    """Breakeven met stop_loss=entry ; initial_stop_loss et R à la clôture utilisent le risque d'ouverture."""
    risk = RiskEngine(initial_capital=10_000.0)
    ex = ExecutionEngine(risk)
    t0 = datetime(2025, 11, 17, 15, 0, tzinfo=timezone.utc)
    placed = ex.place_order(_mk_setup_news_fade_short(), _risk_alloc(), current_time=t0)
    assert placed["success"]
    tid = placed["trade_id"]
    tr = ex.open_trades[tid]
    assert tr.initial_stop_loss == 100.5
    assert abs(tr.entry_price - tr.initial_stop_loss) > 1e-6
    ex.update_open_trades({"SPY": 99.5}, current_time=t0 + timedelta(minutes=1))
    assert tr.breakeven_moved
    assert tr.stop_loss == 100.0
    assert tr.initial_stop_loss == 100.5
    ex.close_trade(tid, "session_end", close_price=99.4, current_time=t0 + timedelta(minutes=2))
    closed = ex.closed_trades[-1]
    assert closed.initial_stop_loss == 100.5
    assert abs(closed.entry_price - closed.initial_stop_loss) > 1e-6
    assert abs(closed.r_multiple - 1.2) < 1e-9


def test_news_fade_rejects_zero_risk_at_open():
    risk = RiskEngine(initial_capital=10_000.0)
    ex = ExecutionEngine(risk)
    t0 = datetime(2025, 11, 17, 15, 0, tzinfo=timezone.utc)
    bad = _mk_setup_news_fade_short()
    bad.entry_price = 100.0
    bad.stop_loss = 100.0
    bad.take_profit_1 = 100.0
    with pytest.raises(ValueError, match="News_Fade"):
        ex.place_order(bad, _risk_alloc(), current_time=t0)


def test_legacy_playbook_breakeven_still_0_5r():
    risk = RiskEngine(initial_capital=10_000.0)
    ex = ExecutionEngine(risk)
    t0 = datetime(2025, 11, 3, 14, 30, tzinfo=timezone.utc)
    setup = _mk_setup_wave1("Session_Open_Scalp", "SCALP")
    setup.playbook_name = "Session_Open_Scalp"
    placed = ex.place_order(setup, _risk_alloc(), current_time=t0)
    tr = ex.open_trades[placed["trade_id"]]
    assert tr.playbook == "Session_Open_Scalp"
    assert tr.breakeven_trigger_rr is None

    ex.update_open_trades({"SPY": 100.5}, current_time=t0 + timedelta(minutes=1))
    assert tr.breakeven_moved is True
    assert tr.stop_loss == 100.0


def test_backtest_lss_time_stop_parity_30m_with_global_120():
    cfg = BacktestConfig(
        data_paths=[],
        symbols=["SPY"],
        start_date="2025-11-01",
        end_date="2025-11-30",
        trading_mode="AGGRESSIVE",
        max_scalp_minutes=120.0,
    )
    engine = BacktestEngine(cfg)
    t0 = datetime(2025, 11, 3, 14, 30, tzinfo=timezone.utc)
    engine.data["SPY"] = pd.DataFrame(
        {
            "datetime": [t0 + timedelta(minutes=i) for i in range(45)],
            "close": [100.0] * 45,
        }
    )
    placed = engine.execution_engine.place_order(
        _mk_setup_wave1("Liquidity_Sweep_Scalp", "SCALP"), _risk_alloc(), current_time=t0
    )
    assert placed["success"]
    engine._update_positions(t0 + timedelta(minutes=35))
    assert len(engine.execution_engine.get_open_trades()) == 0
    assert engine.execution_engine.closed_trades[-1].exit_reason == "time_stop"


def test_legacy_scalp_time_stop_uses_global_cap():
    risk = RiskEngine(initial_capital=10_000.0)
    risk._max_scalp_minutes = 120.0
    ex = ExecutionEngine(risk)
    t0 = datetime(2025, 11, 3, 14, 30, tzinfo=timezone.utc)
    setup = _mk_setup_wave1("Session_Open_Scalp", "SCALP")
    setup.playbook_name = "Session_Open_Scalp"
    placed = ex.place_order(setup, _risk_alloc(), current_time=t0)
    tid = placed["trade_id"]
    ex.update_open_trades({"SPY": 100.1}, current_time=t0 + timedelta(minutes=35))
    assert tid in ex.open_trades
    ex.update_open_trades({"SPY": 100.1}, current_time=t0 + timedelta(minutes=125))
    assert tid not in ex.open_trades
    assert ex.closed_trades[-1].exit_reason == "time_stop"
