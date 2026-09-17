"""The paper-trading pipeline must not fill at the exact target price.

ExecutionEngine keeps IdealFillModel as its bare default (unit tests and
E[R]_gross exploration rely on it), but TradingPipeline is the product path
behind /trading: paper PnL there used to ignore spread and slippage entirely.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_trading_pipeline_uses_conservative_fills():
    from engines.pipeline import TradingPipeline
    from engines.execution.fill_model import ConservativeFillModel

    pipe = TradingPipeline()
    assert isinstance(pipe.execution_engine.fill_model, ConservativeFillModel)
