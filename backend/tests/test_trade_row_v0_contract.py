"""Validation TradeRowV0 sur une ligne parquet réelle (contrat paper)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from contracts.trade_row_v0 import TradeRowV0, parse_trade_row_v0

_BACKEND = Path(__file__).resolve().parent.parent
_SAMPLE_TRADES = _BACKEND / "data" / "backtest_results" / "trades_costs_test_1d_AGGRESSIVE_DAILY.parquet"


@pytest.mark.skipif(not _SAMPLE_TRADES.is_file(), reason="échantillon trades parquet absent")
def test_parse_first_row_from_tracked_parquet() -> None:
    df = pd.read_parquet(_SAMPLE_TRADES)
    assert len(df) >= 1
    row = df.iloc[0].to_dict()
    m = parse_trade_row_v0(row)
    assert isinstance(m, TradeRowV0)
    assert m.symbol in {"SPY", "QQQ"} or len(m.symbol) >= 1
    assert m.trade_type in {"DAILY", "SCALP"}


def test_parse_minimal_synthetic_row() -> None:
    payload = {
        "trade_id": "t1",
        "timestamp_entry": "2025-01-01T10:00:00+00:00",
        "timestamp_exit": "2025-01-01T11:00:00+00:00",
        "symbol": "SPY",
        "playbook": "News_Fade",
        "direction": "LONG",
        "trade_type": "SCALP",
        "entry_price": 100.0,
        "exit_price": 101.0,
        "stop_loss": 99.0,
        "take_profit_1": 102.0,
        "r_multiple": 1.0,
        "outcome": "win",
        "exit_reason": "TP1",
        "duration_minutes": 60.0,
    }
    m = parse_trade_row_v0(payload)
    assert m.playbook == "News_Fade"
