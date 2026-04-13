"""Phase 8 — coûts d'exécution backtest (commissions, fees, slippage, spread)."""
from backtest.costs import (
    calculate_ibkr_commission,
    calculate_regulatory_fees,
    calculate_slippage,
    calculate_spread_cost,
    calculate_total_execution_costs,
)


def test_ibkr_fixed_commission_min_one_dollar():
    c = calculate_ibkr_commission(100, 450.0, "ibkr_fixed")
    assert c >= 1.0


def test_regulatory_fees_zero_on_buy():
    assert calculate_regulatory_fees(100, 450.0, "buy") == 0.0


def test_regulatory_fees_positive_on_sell():
    f = calculate_regulatory_fees(100, 450.0, "sell")
    assert f > 0.0


def test_slippage_pct_and_ticks():
    p = calculate_slippage(100, 100.0, "pct", slippage_pct=0.001)
    t = calculate_slippage(100, 100.0, "ticks", slippage_ticks=2)
    assert p == 10.0
    assert t == 2.0


def test_spread_half_spread_bps():
    s = calculate_spread_cost(100, 200.0, "fixed_bps", spread_bps=4.0)
    assert s == 4.0


def test_total_round_trip_positive():
    entry, exit_ = calculate_total_execution_costs(
        shares=50,
        entry_price=500.0,
        exit_price=501.0,
        commission_model="ibkr_fixed",
        enable_reg_fees=True,
        slippage_model="pct",
        slippage_pct=0.0005,
        spread_model="fixed_bps",
        spread_bps=2.0,
    )
    assert entry.total > 0
    assert exit_.total > 0
    assert entry.commission >= 1.0
    assert exit_.regulatory_fees >= 0.0
