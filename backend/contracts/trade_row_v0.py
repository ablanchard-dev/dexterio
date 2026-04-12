"""TradeRowV0 — une ligne du journal trades (parquet mini-lab / backtest)."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from pydantic import BaseModel, ConfigDict, field_validator


class TradeRowV0(BaseModel):
    """
    Colonnes minimales alignées sur `BACKEND_FRONT_CONTRACTS_PAPER_LIVE.md`.
    Les parquets réels peuvent contenir des colonnes additionnelles (ignorées).
    """

    model_config = ConfigDict(extra="ignore")

    trade_id: str
    timestamp_entry: datetime
    timestamp_exit: datetime
    symbol: str
    playbook: str
    direction: str
    trade_type: str
    entry_price: float
    exit_price: float
    stop_loss: float
    take_profit_1: float
    r_multiple: float
    outcome: str
    exit_reason: str
    duration_minutes: float

    @field_validator("timestamp_entry", "timestamp_exit", mode="before")
    @classmethod
    def _coerce_pandas_ts(cls, v: Any) -> Any:
        if hasattr(v, "to_pydatetime"):
            return v.to_pydatetime()
        return v


def parse_trade_row_v0(row: Dict[str, Any]) -> TradeRowV0:
    return TradeRowV0.model_validate(row)
