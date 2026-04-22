"""Phase W.2 — FillModel is held by ExecutionEngine, default IdealFillModel.

Locks the contract so future callers can rely on `engine.fill_model` and on
being able to inject a ConservativeFillModel for paper/live realism.
"""
from __future__ import annotations

import sys
from pathlib import Path


def _backend_dir() -> Path:
    return Path(__file__).parent.parent


sys.path.insert(0, str(_backend_dir()))


def test_default_fill_model_is_ideal():
    from engines.execution.paper_trading import ExecutionEngine
    from engines.execution.fill_model import IdealFillModel
    from engines.risk_engine import RiskEngine

    eng = ExecutionEngine(RiskEngine())
    assert isinstance(eng.fill_model, IdealFillModel)


def test_conservative_fill_model_can_be_injected():
    from engines.execution.paper_trading import ExecutionEngine
    from engines.execution.fill_model import ConservativeFillModel
    from engines.risk_engine import RiskEngine

    conservative = ConservativeFillModel(extra_slippage_pct=0.0005)
    eng = ExecutionEngine(RiskEngine(), fill_model=conservative)
    assert eng.fill_model is conservative


def test_default_clock_mode_is_backtest():
    from engines.execution.paper_trading import ExecutionEngine, ClockMode
    from engines.risk_engine import RiskEngine

    eng = ExecutionEngine(RiskEngine())
    assert eng.clock_mode == ClockMode.BACKTEST


def test_clock_mode_can_be_set_to_paper_or_live():
    from engines.execution.paper_trading import ExecutionEngine, ClockMode
    from engines.risk_engine import RiskEngine

    eng_paper = ExecutionEngine(RiskEngine(), clock_mode=ClockMode.PAPER)
    assert eng_paper.clock_mode == ClockMode.PAPER

    eng_live = ExecutionEngine(RiskEngine(), clock_mode=ClockMode.LIVE)
    assert eng_live.clock_mode == ClockMode.LIVE
