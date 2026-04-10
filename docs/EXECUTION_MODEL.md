# EXECUTION MODEL

## Modes

### 1) Backtest execution
- Driver: chronological replay (1m base).
- Execution engine: `ExecutionEngine` in simulated mode.
- Costs: commission/spread/slippage modeled via backtest config and cost utilities.
- Artifacts: summary, trades, equity, debug outputs.

### 2) Paper runtime execution
- API control: `/api/trading/control` start/stop/close_all.
- Loop: scheduler runs analysis + position updates repeatedly.
- Orders: local paper engine (`paper_trading.py`).

### 3) Live-prep execution
- IBKR connectivity probe exists (`ibkr_connection_check`).
- Live backend flag exists (`EXECUTION_BACKEND=ibkr`, `LIVE_TRADING_ENABLED=true`).
- Current limitation: order-routing/bracket adapter is not yet fully wired in `ExecutionEngine`.

## Trade lifecycle (implemented)
1. Candidate setup generated.
2. Risk gate checks.
3. Position sizing computed.
4. Order opened in paper engine.
5. Position updated each loop tick (SL/TP/time-stop/breakeven).
6. Trade closed and journaled.

## Required gate for true live readiness (not yet fully enforced in code)
- Sustained paper profitability period.
- Hard drawdown and loss caps validated in forward conditions.
- Reconciliation and fail-safe restart tests passed.
- Broker adapter tested with mocks and controlled canary size.

