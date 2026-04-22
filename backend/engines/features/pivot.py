"""Shared Pivot dataclass.

Used by:
    features.directional_change — produces pivots from ATR-adaptive zigzag.
    execution.tp_resolver       — consumes pivots to locate liquidity draws.

Frozen so pivots can live in caches keyed by (symbol, last_bar_idx, kappas).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

PivotType = Literal["high", "low"]


@dataclass(frozen=True)
class Pivot:
    index: int
    price: float
    type: PivotType
    timestamp: datetime
