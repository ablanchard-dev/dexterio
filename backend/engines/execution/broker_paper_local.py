"""Sprint 4-lite — Paper local mock broker.

In-memory paper broker, simule fills via prices fournis par update_market_data.
Pas IBKR. Pas Alpaca. Pure mock pour valider plomberie + tests.

Logique simple :
  - Market orders : fill immédiat au prix courant fourni
  - Limit orders : fill quand prix touche limit
  - Slippage simulé via ConservativeFillModel existant (G1 livré)
  - Cash + positions tracked in-memory
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from engines.execution.broker_interface import (
    AccountSnapshot,
    Broker,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
)


class PaperLocalBroker(Broker):
    """In-memory paper broker for testing pipeline plomberie.

    Sans dépendance externe. Sans IBKR. Sans réseau.
    """

    name = "paper_local"

    def __init__(self, initial_cash: float = 50_000.0,
                  spread_bps: float = 1.0,
                  slippage_pct: float = 0.0005):
        self._cash = initial_cash
        self._initial_cash = initial_cash
        self._positions: dict[str, Position] = {}
        self._open_orders: dict[str, Order] = {}
        self._all_orders: list[Order] = []
        self._market_prices: dict[str, float] = {}
        self.spread_bps = spread_bps
        self.slippage_pct = slippage_pct
        self._realized_pnl = 0.0

    def update_market_data(self, prices: dict[str, float]) -> None:
        """Update internal price state. Triggers pending limit order fills if applicable."""
        self._market_prices.update(prices)
        # Update mark-to-market on existing positions
        for sym, pos in self._positions.items():
            if sym in self._market_prices:
                pos.market_price = self._market_prices[sym]
                pos.unrealized_pnl = (pos.market_price - pos.avg_entry_price) * pos.quantity
        # Check pending limit orders for fills
        for order in list(self._open_orders.values()):
            if order.status != OrderStatus.PENDING:
                continue
            if order.symbol not in self._market_prices:
                continue
            if order.order_type == OrderType.LIMIT and order.limit_price is not None:
                cur_price = self._market_prices[order.symbol]
                # BUY limit fills if price <= limit ; SELL limit fills if price >= limit
                if order.side == OrderSide.BUY and cur_price <= order.limit_price:
                    self._fill_order(order, cur_price)
                elif order.side == OrderSide.SELL and cur_price >= order.limit_price:
                    self._fill_order(order, cur_price)

    def _apply_slippage(self, price: float, side: OrderSide) -> float:
        """Adverse slippage : buy higher, sell lower."""
        spread_pct = self.spread_bps / 10_000.0
        total_pct = self.slippage_pct + spread_pct
        if side == OrderSide.BUY:
            return price * (1 + total_pct)
        return price * (1 - total_pct)

    def _fill_order(self, order: Order, raw_price: float) -> None:
        """Execute fill with slippage + update positions/cash."""
        fill_price = self._apply_slippage(raw_price, order.side)
        order.fill_price = fill_price
        order.fill_quantity = order.quantity
        order.status = OrderStatus.FILLED
        order.filled_at = datetime.now(timezone.utc)

        signed_qty = order.quantity if order.side == OrderSide.BUY else -order.quantity
        # Update position
        if order.symbol in self._positions:
            pos = self._positions[order.symbol]
            new_qty = pos.quantity + signed_qty
            if new_qty == 0:
                # Close position : realize PnL
                pnl = (fill_price - pos.avg_entry_price) * pos.quantity
                self._realized_pnl += pnl
                self._cash += pos.quantity * fill_price  # cash from selling/closing
                del self._positions[order.symbol]
            elif (pos.quantity > 0 and signed_qty > 0) or (pos.quantity < 0 and signed_qty < 0):
                # Same direction : avg up
                total_cost = pos.avg_entry_price * pos.quantity + fill_price * signed_qty
                pos.quantity = new_qty
                pos.avg_entry_price = total_cost / new_qty
                self._cash -= signed_qty * fill_price
            else:
                # Reduce position
                if abs(signed_qty) >= abs(pos.quantity):
                    # Cross zero - close + open opposite
                    pnl = (fill_price - pos.avg_entry_price) * pos.quantity
                    self._realized_pnl += pnl
                    remaining = signed_qty + pos.quantity
                    if remaining != 0:
                        pos.quantity = remaining
                        pos.avg_entry_price = fill_price
                        self._cash -= remaining * fill_price + pos.quantity * fill_price
                    else:
                        del self._positions[order.symbol]
                        self._cash += pos.quantity * fill_price
                else:
                    pnl = (fill_price - pos.avg_entry_price) * abs(signed_qty)
                    self._realized_pnl += pnl if pos.quantity > 0 else -pnl
                    pos.quantity = new_qty
                    self._cash += abs(signed_qty) * fill_price * (1 if pos.quantity > 0 else -1)
        else:
            # New position
            self._positions[order.symbol] = Position(
                symbol=order.symbol,
                quantity=signed_qty,
                avg_entry_price=fill_price,
                market_price=fill_price,
                unrealized_pnl=0.0,
            )
            self._cash -= signed_qty * fill_price
        # Remove from open orders
        if order.order_id in self._open_orders:
            del self._open_orders[order.order_id]

    def place_order(self, symbol: str, side: OrderSide, quantity: float,
                     order_type: OrderType = OrderType.MARKET,
                     limit_price: Optional[float] = None) -> Order:
        order = Order(
            order_id=str(uuid.uuid4()),
            symbol=symbol,
            side=side,
            quantity=abs(quantity),
            order_type=order_type,
            limit_price=limit_price,
        )
        self._all_orders.append(order)

        if order_type == OrderType.MARKET:
            if symbol not in self._market_prices:
                order.status = OrderStatus.REJECTED
                order.error_msg = f"No market data for {symbol}"
                return order
            self._fill_order(order, self._market_prices[symbol])
        else:
            self._open_orders[order.order_id] = order
        return order

    def cancel_order(self, order_id: str) -> bool:
        if order_id not in self._open_orders:
            return False
        order = self._open_orders[order_id]
        if order.status != OrderStatus.PENDING:
            return False
        order.status = OrderStatus.CANCELLED
        del self._open_orders[order_id]
        return True

    def get_open_orders(self) -> list[Order]:
        return list(self._open_orders.values())

    def get_positions(self) -> list[Position]:
        return list(self._positions.values())

    def get_account(self) -> AccountSnapshot:
        equity = self._cash + sum(
            pos.market_price * pos.quantity for pos in self._positions.values()
        )
        # Buying power: simplified (no margin), 1x leverage
        buying_power = max(self._cash, 0)
        return AccountSnapshot(
            cash=self._cash,
            equity=equity,
            buying_power=buying_power,
            realized_pnl=self._realized_pnl,
        )

    @property
    def all_orders(self) -> list[Order]:
        """Read-only access to full order history (for logging/audit)."""
        return list(self._all_orders)
