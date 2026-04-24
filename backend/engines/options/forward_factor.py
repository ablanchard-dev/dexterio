"""F6 Options Forward-Factor — scoping skeleton + data gate.

**STATUS : GATE DATA Cas A §20 — BLOCKED pending user data source**

Source : TRUE `6ao3uXE5KhU` Volatility Vibes ("Forward Factor Options SPY
Strategy") — 27% CAGR / 2.4 Sharpe / 19 ans backtest. Long calendar spread
piloté par Forward Factor = (IV_front − IV_forward) / IV_forward ≥ 0.20.

**Signal formula** :
    FF = (IV_front_month - IV_forward_month) / IV_forward_month
    Entry : FF ≥ 0.20 (implied forward contango exceeds threshold)
    Structure : ATM calendar spread OR ±35Δ double calendar
    Hold : until front expiration
    Sizing : quarter Kelly + cap 4% per position + 20-30 concurrent names

**Data requis (NON DISPONIBLE repo v4.1)** :
- Options chain historique per expiry per strike : bid/ask + IV + Greeks
- Sources possibles :
    * Polygon options REST API (paid, historical back to 2014)
    * OptionMetrics (academic, expensive)
    * ORATS (pro-grade options data)
    * CBOE DataShop (official, pricey)
    * Interactive Brokers historical (via tws-api, 60 days only)
    * yfinance : current chain only, NOT historical IV time-series

**Escalade §0.3 point 5** : F6 smoke impossible sans data. User doit :
    (a) Fournir data source options historique (Polygon subscription or similar)
    (b) OR accepter F6 reporté post-F2 validation + paper baseline

**Ce module reste un skeleton** : interfaces définies, compute functions
stubbed, backtest impossible sans data. Test skeleton garanti (logic pure
sur fixture synthetic) — pas de wiring ExecutionEngine avant data available.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal, Optional


@dataclass(frozen=True)
class OptionContract:
    """Single option contract snapshot (for reference — not in repo data)."""

    underlying: str
    expiry: date
    strike: float
    option_type: Literal["call", "put"]
    bid: float
    ask: float
    implied_volatility: float
    delta: float
    theta: float
    vega: float
    observed_at: datetime


@dataclass(frozen=True)
class ForwardFactorSignal:
    """Emitted signal on FF threshold breach."""

    as_of: datetime
    underlying: str
    front_expiry: date
    forward_expiry: date
    iv_front: float
    iv_forward: float
    forward_factor: float
    signal_direction: Literal["long_calendar", "skip"]
    recommended_structure: str  # "ATM" | "double_35delta"


def compute_forward_factor(iv_front: float, iv_forward: float) -> float:
    """Compute Forward Factor = (IV_front - IV_forward) / IV_forward.

    Pure math, no data dependency. Useful once options chain data is loaded.
    Returns 0.0 if iv_forward is non-positive (defensive).
    """
    if iv_forward <= 0:
        return 0.0
    return (iv_front - iv_forward) / iv_forward


def classify_signal(
    forward_factor: float, threshold: float = 0.20
) -> Literal["long_calendar", "skip"]:
    """Binary classifier : long calendar if FF exceeds threshold, else skip."""
    return "long_calendar" if forward_factor >= threshold else "skip"


# --- Data gate helper --------------------------------------------------

DATA_GATE_MESSAGE = """
F6 Options Forward-Factor data gap :

Required data NOT available in repo v4.1 :
  - Historical SPY options chain (expiry × strike × IV × Greeks)
  - Minimum viable : 5 years daily snapshots of ATM ± 10 strikes for the
    2 front expiries.

Possible sources :
  - Polygon.io options REST API (subscription ~$200/mo, historical back to 2014)
  - OptionMetrics via WRDS (academic, ~$5k/yr institutional)
  - ORATS (pro-grade, subscription)
  - CBOE DataShop (pay-per-dataset)

User decision required (plan v4.0 §0.3 point 5) :
  (a) Provide data source → F6 smoke possible
  (b) Defer F6 post-F2 validation → F2 priority
  (c) Alternative : synthetic options via Black-Scholes reconstruction
      from SPY 1m data + VIX (less rigorous, exploratory only)
"""


def data_gate_status() -> dict:
    """Structured verdict on F6 data readiness."""
    return {
        "data_available": False,
        "can_backtest": False,
        "reason": "options chain historical not in repo",
        "escalation": "§0.3 point 5 : user data source decision",
        "message": DATA_GATE_MESSAGE,
    }
