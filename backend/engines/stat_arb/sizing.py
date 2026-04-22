"""Beta-neutral pair sizing.

Given a dollar-risk budget R_$ and beta, size two legs so that:
  qty_y * price_y = R_$_leg_y
  qty_x * price_x = beta * qty_y * price_y

i.e. dollar exposure of leg x = beta * dollar exposure of leg y.
Legs are signed: ARMED_LONG → +y/-x (buy y, sell x); ARMED_SHORT → -y/+x.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class PairSize:
    qty_y: int  # signed shares for leg y (spread's numerator)
    qty_x: int  # signed shares for leg x (spread's denominator)
    notional_y: float
    notional_x: float


def pair_sizing(
    risk_dollars: float,
    price_y: float,
    price_x: float,
    beta: float,
    direction: Literal["long", "short"],
    stop_distance_r_dollars: float,
) -> PairSize:
    """Compute beta-neutral pair sizes.

    risk_dollars            : total $ risk budget for the pair (both legs).
    stop_distance_r_dollars : expected $-loss at SL on leg y (spread move * notional).

    Since SPY/QQQ z-score SL is defined in spread-space, caller provides
    equivalent per-leg stop distance in $. We size leg y so that hitting
    SL loses ~ risk_dollars total (accounting for correlated leg x move).
    """
    if price_y <= 0 or price_x <= 0:
        raise ValueError("prices must be positive")
    if beta <= 0:
        raise ValueError(f"beta must be positive, got {beta}")
    if stop_distance_r_dollars <= 0:
        raise ValueError("stop_distance_r_dollars must be positive")

    qty_y_abs = max(1, int(risk_dollars / stop_distance_r_dollars))
    qty_x_abs = max(1, int(round(qty_y_abs * price_y * beta / price_x)))

    if direction == "long":
        qty_y = qty_y_abs
        qty_x = -qty_x_abs
    elif direction == "short":
        qty_y = -qty_y_abs
        qty_x = qty_x_abs
    else:
        raise ValueError(f"direction must be 'long' or 'short', got {direction!r}")

    return PairSize(
        qty_y=qty_y,
        qty_x=qty_x,
        notional_y=qty_y * price_y,
        notional_x=qty_x * price_x,
    )
