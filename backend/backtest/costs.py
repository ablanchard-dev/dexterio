"""
PHASE B - Execution Costs Model
Realistic simulation of trading costs for backtesting

Simulates:
- IBKR commissions (fixed / tiered)
- US regulatory fees (SEC + FINRA)
- Slippage (percentage or ticks)
- Spread cost (bid-ask implicit cost)

Usage:
    from backtest.costs import calculate_total_execution_costs
    
    entry_costs, exit_costs = calculate_total_execution_costs(
        shares=100,
        entry_price=450.50,
        exit_price=452.75,
        commission_model="ibkr_fixed",
        slippage_model="pct"
    )
"""

from dataclasses import dataclass
from typing import Literal


@dataclass
class ExecutionCosts:
    """Breakdown of execution costs for a single order"""
    commission: float
    regulatory_fees: float
    slippage: float
    spread_cost: float
    total: float


def calculate_ibkr_commission(
    shares: int,
    price: float,
    model: Literal["ibkr_fixed", "ibkr_tiered", "none"]
) -> float:
    """
    Calculate IBKR commission for US stocks/ETFs
    
    Models:
    - ibkr_fixed: $0.005/share, min $1.00, max 1% of trade value
    - ibkr_tiered: $0.0035/share, min $0.35, max 1% (volume discounts)
    - none: $0.00
    
    Args:
        shares: Number of shares
        price: Price per share
        model: Commission model
    
    Returns:
        Commission in dollars
    
    References:
    - https://www.interactivebrokers.com/en/pricing/commissions-stocks.php
    """
    if model == "none":
        return 0.0
    
    trade_value = shares * price
    
    if model == "ibkr_fixed":
        commission = shares * 0.005
        commission = max(commission, 1.0)
        commission = min(commission, trade_value * 0.01)
    
    elif model == "ibkr_tiered":
        # Tiered pricing (simplified, assumes high volume tier)
        commission = shares * 0.0035
        commission = max(commission, 0.35)
        commission = min(commission, trade_value * 0.01)
    
    else:
        commission = 0.0
    
    return round(commission, 2)


def calculate_regulatory_fees(
    shares: int,
    price: float,
    side: Literal["buy", "sell"]
) -> float:
    """
    Calculate US regulatory fees
    
    Fees (applied on SELLS only):
    - SEC fee: $5.10 per $1,000,000 (2024 rate)
    - FINRA TAF: $0.000145 per share, max $7.27 per trade
    
    Args:
        shares: Number of shares
        price: Price per share
        side: "buy" or "sell"
    
    Returns:
        Total regulatory fees in dollars
    
    References:
    - https://www.sec.gov/info/smallbus/secg/transactionfees
    - https://www.finra.org/filing-reporting/taf
    """
    if side == "buy":
        return 0.0
    
    trade_value = shares * price
    
    # SEC Transaction Fee (sell only)
    sec_fee = (trade_value / 1_000_000) * 5.10
    
    # FINRA Trading Activity Fee (sell only)
    finra_taf = shares * 0.000145
    finra_taf = min(finra_taf, 7.27)
    
    total = sec_fee + finra_taf
    return round(total, 2)


def calculate_slippage(
    shares: int,
    price: float,
    model: Literal["pct", "ticks", "none"],
    slippage_pct: float = 0.0005,  # 0.05% default
    slippage_ticks: int = 1
) -> float:
    """
    Calculate slippage cost
    
    Slippage = difference between expected price and actual execution price
    
    Models:
    - pct: Fixed percentage of trade value
    - ticks: Fixed number of price ticks ($0.01 for stocks)
    - none: No slippage
    
    Args:
        shares: Number of shares
        price: Price per share
        model: Slippage model
        slippage_pct: Percentage slippage (e.g., 0.0005 = 0.05%)
        slippage_ticks: Number of ticks (1 tick = $0.01)
    
    Returns:
        Slippage cost in dollars
    """
    if model == "none":
        return 0.0
    
    if model == "pct":
        slippage = shares * price * slippage_pct
    
    elif model == "ticks":
        # 1 tick = $0.01 for US stocks
        tick_size = 0.01
        slippage = shares * slippage_ticks * tick_size
    
    else:
        slippage = 0.0
    
    return round(slippage, 2)


def calculate_spread_cost(
    shares: int,
    price: float,
    model: Literal["none", "fixed_bps"],
    spread_bps: float = 2.0  # 2 bps = 0.02% default
) -> float:
    """
    Calculate bid-ask spread implicit cost
    
    Spread cost = half of the bid-ask spread (implicit cost of crossing spread)
    
    Models:
    - fixed_bps: Fixed spread in basis points (1 bp = 0.01%)
    - none: No spread cost
    
    Args:
        shares: Number of shares
        price: Mid-price
        model: Spread model
        spread_bps: Spread in basis points
    
    Returns:
        Spread cost in dollars
    
    Note:
        For SPY/QQQ, typical spread is 1-3 bps during normal hours
    """
    if model == "none":
        return 0.0
    
    if model == "fixed_bps":
        # Spread cost = (shares * price * spread_bps / 10000) * 0.5
        # Factor 0.5 because we only pay half the spread
        spread_cost = shares * price * (spread_bps / 10000) * 0.5
    
    else:
        spread_cost = 0.0
    
    return round(spread_cost, 2)


def calculate_total_execution_costs(
    shares: int,
    entry_price: float,
    exit_price: float,
    commission_model: str = "ibkr_fixed",
    enable_reg_fees: bool = True,
    slippage_model: str = "pct",
    slippage_pct: float = 0.0005,
    slippage_ticks: int = 1,
    spread_model: str = "fixed_bps",
    spread_bps: float = 2.0
) -> tuple[ExecutionCosts, ExecutionCosts]:
    """
    Calculate total execution costs for entry and exit
    
    Args:
        shares: Position size in shares
        entry_price: Entry price per share
        exit_price: Exit price per share
        commission_model: "ibkr_fixed", "ibkr_tiered", "none"
        enable_reg_fees: Enable regulatory fees calculation
        slippage_model: "pct", "ticks", "none"
        slippage_pct: Percentage slippage (if model=pct)
        slippage_ticks: Tick slippage (if model=ticks)
        spread_model: "fixed_bps", "none"
        spread_bps: Spread in basis points
    
    Returns:
        Tuple of (entry_costs, exit_costs)
    
    Example:
        >>> entry, exit = calculate_total_execution_costs(
        ...     shares=100,
        ...     entry_price=450.50,
        ...     exit_price=452.75,
        ...     commission_model="ibkr_fixed"
        ... )
        >>> print(f"Total costs: ${entry.total + exit.total:.2f}")
    """
    # Entry costs (BUY)
    entry_commission = calculate_ibkr_commission(shares, entry_price, commission_model)
    entry_reg_fees = calculate_regulatory_fees(shares, entry_price, "buy") if enable_reg_fees else 0.0
    entry_slippage = calculate_slippage(shares, entry_price, slippage_model, slippage_pct, slippage_ticks)
    entry_spread = calculate_spread_cost(shares, entry_price, spread_model, spread_bps)
    
    entry_costs = ExecutionCosts(
        commission=entry_commission,
        regulatory_fees=entry_reg_fees,
        slippage=entry_slippage,
        spread_cost=entry_spread,
        total=entry_commission + entry_reg_fees + entry_slippage + entry_spread
    )
    
    # Exit costs (SELL)
    exit_commission = calculate_ibkr_commission(shares, exit_price, commission_model)
    exit_reg_fees = calculate_regulatory_fees(shares, exit_price, "sell") if enable_reg_fees else 0.0
    exit_slippage = calculate_slippage(shares, exit_price, slippage_model, slippage_pct, slippage_ticks)
    exit_spread = calculate_spread_cost(shares, exit_price, spread_model, spread_bps)
    
    exit_costs = ExecutionCosts(
        commission=exit_commission,
        regulatory_fees=exit_reg_fees,
        slippage=exit_slippage,
        spread_cost=exit_spread,
        total=exit_commission + exit_reg_fees + exit_slippage + exit_spread
    )
    
    return entry_costs, exit_costs


# ==============================================================================
# Utility functions
# ==============================================================================

def get_default_costs_config() -> dict:
    """
    Get default costs configuration (IBKR realistic)
    
    Returns:
        Dictionary with default cost parameters
    """
    return {
        "commission_model": "ibkr_fixed",
        "enable_reg_fees": True,
        "slippage_model": "pct",
        "slippage_pct": 0.0005,  # 0.05%
        "slippage_ticks": 1,
        "spread_model": "fixed_bps",
        "spread_bps": 2.0  # 2 bps
    }


def estimate_total_cost_percentage(
    entry_price: float,
    commission_model: str = "ibkr_fixed",
    slippage_pct: float = 0.0005,
    spread_bps: float = 2.0
) -> float:
    """
    Estimate total round-trip cost as percentage of trade value
    
    Useful for quick "cost check" before backtesting
    
    Args:
        entry_price: Entry price per share
        commission_model: Commission model
        slippage_pct: Slippage percentage
        spread_bps: Spread in basis points
    
    Returns:
        Estimated cost percentage (e.g., 0.0015 = 0.15%)
    """
    # Estimate for 100 shares (typical position)
    shares = 100
    
    entry_costs, exit_costs = calculate_total_execution_costs(
        shares=shares,
        entry_price=entry_price,
        exit_price=entry_price,  # Assume breakeven
        commission_model=commission_model,
        slippage_model="pct",
        slippage_pct=slippage_pct,
        spread_model="fixed_bps",
        spread_bps=spread_bps
    )
    
    total_cost = entry_costs.total + exit_costs.total
    trade_value = shares * entry_price
    
    return total_cost / trade_value


if __name__ == "__main__":
    # Example usage
    print("=" * 80)
    print("PHASE B - Execution Costs Model - Example")
    print("=" * 80)
    
    # Example: 100 shares SPY @ $450
    shares = 100
    entry_price = 450.50
    exit_price = 452.75  # +$2.25 profit per share
    
    print(f"\nTrade: {shares} shares @ ${entry_price:.2f} → ${exit_price:.2f}")
    print(f"Gross P&L: ${(exit_price - entry_price) * shares:.2f}")
    
    # Calculate costs
    entry_costs, exit_costs = calculate_total_execution_costs(
        shares=shares,
        entry_price=entry_price,
        exit_price=exit_price,
        commission_model="ibkr_fixed",
        enable_reg_fees=True,
        slippage_model="pct",
        slippage_pct=0.0005,
        spread_model="fixed_bps",
        spread_bps=2.0
    )
    
    print(f"\n📊 Entry Costs:")
    print(f"  Commission:      ${entry_costs.commission:.2f}")
    print(f"  Reg Fees:        ${entry_costs.regulatory_fees:.2f}")
    print(f"  Slippage:        ${entry_costs.slippage:.2f}")
    print(f"  Spread:          ${entry_costs.spread_cost:.2f}")
    print(f"  Total Entry:     ${entry_costs.total:.2f}")
    
    print(f"\n📊 Exit Costs:")
    print(f"  Commission:      ${exit_costs.commission:.2f}")
    print(f"  Reg Fees:        ${exit_costs.regulatory_fees:.2f}")
    print(f"  Slippage:        ${exit_costs.slippage:.2f}")
    print(f"  Spread:          ${exit_costs.spread_cost:.2f}")
    print(f"  Total Exit:      ${exit_costs.total:.2f}")
    
    total_costs = entry_costs.total + exit_costs.total
    gross_pnl = (exit_price - entry_price) * shares
    net_pnl = gross_pnl - total_costs
    
    print(f"\n💰 Final P&L:")
    print(f"  Gross:           ${gross_pnl:.2f}")
    print(f"  Total Costs:     ${total_costs:.2f}")
    print(f"  Net:             ${net_pnl:.2f}")
    print(f"  Cost %:          {(total_costs / (shares * entry_price) * 100):.3f}%")
    
    print("\n" + "=" * 80)
