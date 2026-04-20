"""Fill-model abstraction for execution engine.

Two implementations, same interface:

- IdealFillModel: reproduces the current ExecutionEngine behavior — fill at the
  target price exactly (SL at stop_loss, TP at take_profit_1/2, market at bar close).
  Slippage/commissions/spread are applied separately by `backend.backtest.costs`.
- ConservativeFillModel: fills a bar-level order at the NEXT bar's open when one is
  available, and applies an additional adverse slippage multiplier on top of the
  cost-model slippage. Used to simulate realistic paper/live execution in the
  reconcile harness.

This is a protocol, not a refactor — `paper_trading.ExecutionEngine` still uses its
own inline logic by default. The engine can be opted into a FillModel (future wire)
or, more immediately, the reconcile harness uses these models to compute the
fill-price delta between ideal and conservative.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Protocol

from models.market_data import Candle
from models.trade import Trade


@dataclass
class FillResult:
    """Output of a fill attempt."""
    filled: bool
    fill_price: float
    fill_time: datetime
    reason: str              # 'SL' | 'TP1' | 'TP2' | 'market' | 'stop' | 'limit'
    slippage_adjustment: float = 0.0  # $ per share vs target (positive = adverse to trade)


class FillModel(Protocol):
    """Contract for fill-price computation.

    All methods receive the CURRENT bar (what triggered the fill attempt). The
    `next_bar` argument is optional — conservative fills use it; ideal fills ignore it.
    """

    def fill_stop(self, trade: Trade, bar: Candle,
                  next_bar: Optional[Candle] = None) -> Optional[FillResult]:
        """Fill at the stop_loss level. Return None if bar doesn't reach it."""
        ...

    def fill_take_profit(self, trade: Trade, bar: Candle, tp_level: float,
                         reason: str,
                         next_bar: Optional[Candle] = None) -> Optional[FillResult]:
        """Fill at the TP level. Return None if bar doesn't reach it."""
        ...

    def fill_market(self, trade: Trade, bar: Candle,
                    next_bar: Optional[Candle] = None) -> FillResult:
        """Unconditional market fill (used for time-stop, session-end, etc.)."""
        ...


def _bar_hits_stop(trade: Trade, bar: Candle) -> bool:
    if trade.direction == "LONG":
        return bar.low <= trade.stop_loss
    return bar.high >= trade.stop_loss


def _bar_hits_level(trade: Trade, bar: Candle, level: float) -> bool:
    if trade.direction == "LONG":
        return bar.high >= level
    return bar.low <= level


class IdealFillModel:
    """Current ExecutionEngine behavior: fill at target price, no extra slippage.

    Cost-model slippage from `backend.backtest.costs` is applied downstream on
    `pnl_gross` — not at fill time.
    """

    def fill_stop(self, trade, bar, next_bar=None):
        if not _bar_hits_stop(trade, bar):
            return None
        return FillResult(filled=True, fill_price=trade.stop_loss,
                          fill_time=bar.timestamp, reason="SL",
                          slippage_adjustment=0.0)

    def fill_take_profit(self, trade, bar, tp_level, reason, next_bar=None):
        if not _bar_hits_level(trade, bar, tp_level):
            return None
        return FillResult(filled=True, fill_price=tp_level,
                          fill_time=bar.timestamp, reason=reason,
                          slippage_adjustment=0.0)

    def fill_market(self, trade, bar, next_bar=None):
        return FillResult(filled=True, fill_price=bar.close,
                          fill_time=bar.timestamp, reason="market",
                          slippage_adjustment=0.0)


class ConservativeFillModel:
    """Next-bar-open fills with extra adverse slippage.

    - Stops and TPs that trigger on the current bar fill at the NEXT bar's open
      (if provided) instead of the target price — the signal fires late.
    - Additional slippage = `extra_slippage_pct` of the fill price, always adverse
      to the trade direction.
    - If no `next_bar`, falls back to the ideal target price (end-of-data edge case).
    """

    def __init__(self, extra_slippage_pct: float = 0.0005):
        # 0.05% ≈ double the default cost-model slippage in `backend.backtest.costs`
        self.extra_slippage_pct = extra_slippage_pct

    def _apply_adverse_slippage(self, base_price: float, direction: str) -> tuple[float, float]:
        adj = base_price * self.extra_slippage_pct
        if direction == "LONG":
            # on exit (stop/tp), LONG sells → adverse = sold cheaper → price down
            return base_price - adj, adj
        # SHORT exit buys to cover → adverse = bought more expensive → price up
        return base_price + adj, adj

    def fill_stop(self, trade, bar, next_bar=None):
        if not _bar_hits_stop(trade, bar):
            return None
        base = next_bar.open if next_bar is not None else trade.stop_loss
        price, adj = self._apply_adverse_slippage(base, trade.direction)
        fill_time = next_bar.timestamp if next_bar is not None else bar.timestamp
        return FillResult(filled=True, fill_price=price, fill_time=fill_time,
                          reason="SL", slippage_adjustment=adj)

    def fill_take_profit(self, trade, bar, tp_level, reason, next_bar=None):
        if not _bar_hits_level(trade, bar, tp_level):
            return None
        base = next_bar.open if next_bar is not None else tp_level
        price, adj = self._apply_adverse_slippage(base, trade.direction)
        fill_time = next_bar.timestamp if next_bar is not None else bar.timestamp
        return FillResult(filled=True, fill_price=price, fill_time=fill_time,
                          reason=reason, slippage_adjustment=adj)

    def fill_market(self, trade, bar, next_bar=None):
        base = next_bar.open if next_bar is not None else bar.close
        price, adj = self._apply_adverse_slippage(base, trade.direction)
        fill_time = next_bar.timestamp if next_bar is not None else bar.timestamp
        return FillResult(filled=True, fill_price=price, fill_time=fill_time,
                          reason="market", slippage_adjustment=adj)


__all__ = ["FillModel", "FillResult", "IdealFillModel", "ConservativeFillModel"]
