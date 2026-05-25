"""Sprint 4-lite — Broker interface abstract.

Plomberie minimale broker-agnostic. Pas IBKR yet. Pas TSMOM deploy.

Le but est de fournir une interface stable que toute future stratégie
(quand un edge sera validé) pourra utiliser sans coupler le moteur à un
broker spécifique.

Implémentations concrètes attendues :
  - PaperLocalBroker (mock in-memory, livré dans broker_paper_local.py)
  - IBKRBroker (futur, post-edge-trouvé)
  - AlpacaBroker (futur, alternatif)

Convention : tous les ordres sont identifiés par str id retourné par place_order.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


@dataclass
class Order:
    order_id: str
    symbol: str
    side: OrderSide
    quantity: float
    order_type: OrderType
    limit_price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    fill_price: Optional[float] = None
    fill_quantity: float = 0.0
    placed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    filled_at: Optional[datetime] = None
    error_msg: Optional[str] = None


@dataclass
class Position:
    symbol: str
    quantity: float  # signed : positive = long, negative = short
    avg_entry_price: float
    market_price: float
    unrealized_pnl: float
    realized_pnl: float = 0.0


@dataclass
class AccountSnapshot:
    cash: float
    equity: float  # cash + sum(positions market value)
    buying_power: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    realized_pnl: float = 0.0


class Broker(ABC):
    """Abstract broker interface.

    Tous les brokers concrets (paper local, IBKR, Alpaca) doivent
    implémenter ces 5 méthodes a minima.
    """

    name: str = "abstract"

    @abstractmethod
    def place_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        order_type: OrderType = OrderType.MARKET,
        limit_price: Optional[float] = None,
    ) -> Order:
        """Place an order. Returns Order with order_id assigned."""
        raise NotImplementedError

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order. Returns True if cancelled, False if already filled/rejected."""
        raise NotImplementedError

    @abstractmethod
    def get_open_orders(self) -> list[Order]:
        """Return list of currently pending/open orders."""
        raise NotImplementedError

    @abstractmethod
    def get_positions(self) -> list[Position]:
        """Return list of open positions (qty != 0)."""
        raise NotImplementedError

    @abstractmethod
    def get_account(self) -> AccountSnapshot:
        """Return current account snapshot."""
        raise NotImplementedError

    @abstractmethod
    def update_market_data(self, prices: dict[str, float]) -> None:
        """Update internal price state for mark-to-market and pending order fills.

        For paper/live brokers, this might be a no-op (broker has its own data feed).
        For mock paper broker, this is how the runtime injects price ticks.
        """
        raise NotImplementedError
