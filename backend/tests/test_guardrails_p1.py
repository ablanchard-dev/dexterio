from datetime import datetime, timedelta, timezone

import pandas as pd

from backtest.engine import BacktestEngine
from engines.execution.paper_trading import ExecutionEngine
from engines.risk_engine import CIRCUIT_STOP_RUN_DD_R, RiskEngine
from models.backtest import BacktestConfig
from models.risk import PositionSizingResult
from models.setup import Setup


def _mk_setup(trade_type: str = "SCALP") -> Setup:
    return Setup(
        symbol="SPY",
        direction="LONG",
        quality="A",
        final_score=0.8,
        playbook_name="Session_Open_Scalp" if trade_type == "SCALP" else "NY_Open_Reversal",
        trade_type=trade_type,
        entry_price=100.0,
        stop_loss=99.0,
        take_profit_1=101.0,
        take_profit_2=102.0,
        risk_reward=2.0,
        market_bias="bullish",
        session="NY",
        playbook_matches=[],
    )


def _mk_risk_alloc() -> dict:
    return {
        "risk_pct": 0.01,
        "risk_tier": 1.0,
        "risk_dollars": 100.0,
        "position_calc": PositionSizingResult(
            risk_amount=100.0,
            position_size=100.0,
            risk_tier=1.0,
            distance_stop=1.0,
            multiplier=1.0,
            valid=True,
        ),
    }


def test_time_stop_unit_closes_scalp_once_and_caps_duration():
    risk = RiskEngine(initial_capital=10_000.0)
    risk._max_scalp_minutes = 120.0
    exec_engine = ExecutionEngine(risk)
    setup = _mk_setup("SCALP")

    t0 = datetime(2025, 11, 3, 14, 30, tzinfo=timezone.utc)
    placed = exec_engine.place_order(setup, _mk_risk_alloc(), current_time=t0)
    assert placed["success"] is True
    trade_id = placed["trade_id"]

    # Gros saut temporel: la clôture time-stop doit rester unique et la durée clampée.
    events = exec_engine.update_open_trades({"SPY": 100.1}, current_time=t0 + timedelta(minutes=4000))
    assert any(e["event_type"] == "TIME_STOP" for e in events)
    assert trade_id not in exec_engine.open_trades
    assert len(exec_engine.closed_trades) == 1
    assert exec_engine.closed_trades[0].exit_reason == "time_stop"
    assert exec_engine.closed_trades[0].duration_minutes <= 120.0


def test_time_stop_integration_backtest_guardrail_forces_close():
    cfg = BacktestConfig(
        data_paths=[],
        symbols=["SPY"],
        start_date="2025-11-01",
        end_date="2025-11-30",
        trading_mode="AGGRESSIVE",
        max_scalp_minutes=120.0,
    )
    engine = BacktestEngine(cfg)

    # Données minimales pour _update_positions
    t0 = datetime(2025, 11, 3, 14, 30, tzinfo=timezone.utc)
    t1 = t0 + timedelta(minutes=1)
    df = pd.DataFrame(
        {
            "datetime": [t0, t1],
            "close": [100.0, 100.2],
        }
    )
    engine.data["SPY"] = df

    placed = engine.execution_engine.place_order(_mk_setup("SCALP"), _mk_risk_alloc(), current_time=t0)
    assert placed["success"] is True

    engine._update_positions(t0 + timedelta(minutes=500))
    assert len(engine.execution_engine.get_open_trades()) == 0
    assert len(engine.execution_engine.get_closed_trades()) == 1
    closed = engine.execution_engine.get_closed_trades()[0]
    assert closed.exit_reason == "time_stop"
    assert closed.duration_minutes <= cfg.max_scalp_minutes


def test_stop_run_integration_sets_flag_and_blocks_new_setups():
    cfg = BacktestConfig(
        data_paths=[],
        symbols=["SPY"],
        trading_mode="AGGRESSIVE",
    )
    engine = BacktestEngine(cfg)

    # Force la condition CB et vérifie l'application runtime.
    engine.risk_engine.state.max_drawdown_r = CIRCUIT_STOP_RUN_DD_R + 1.0
    now = datetime(2025, 11, 5, 15, 0, tzinfo=timezone.utc)
    engine._check_circuit_breakers_after_trades(now)

    assert engine._stop_run_triggered is True
    assert engine.risk_engine.state.run_stopped is True

    allowed = engine._execute_setup(_mk_setup("DAILY"), now)
    assert allowed is False
