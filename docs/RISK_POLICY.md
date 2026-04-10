# RISK POLICY (as implemented)

## Policy hierarchy
1. **Hard stops / circuit breakers**
2. **Playbook authorization**
3. **Daily/session caps and cooldown**
4. **Position sizing and 2R/1R transitions**

## Implemented controls

### R1 - Playbook allow/deny authority
- Source: `backend/engines/risk_engine.py`
- Mode-specific allowlist + global denylist.
- Kill-switched playbooks are force-disabled.

### R2 - Circuit breakers
- Stop-day threshold on daily R.
- Stop-run threshold on max drawdown R.
- Per-symbol daily trade caps.

### R3 - Cooldown and anti-spam
- Per `(symbol, playbook)` cooldown timers.
- Per session key limits by playbook.

### R4 - Tiered risk state machine (2R/1R)
- Source: `backend/models/risk.py`, `risk_engine.py`
- Win/loss transitions modify next-trade risk tier.

### R5 - Position sizing
- ETF and futures sizing pathways exist.
- Invalid stop distance or capital constraints trigger reject.

### R6 - No-trade lock conditions
- Daily limits reached
- Circuit breaker hit
- Unauthorized playbook
- Cooldown/session caps reached
- Invalid position sizing

## Operational notes
- Eval flags (`RISK_EVAL_*`) are present for research/audit and should not be active in production.
- Risk engine is the final gate before execution in both backtest and runtime loop.

