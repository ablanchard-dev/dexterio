# NO TRADE RULES

## Principle
A valid system output is often "no trade". Rejection is required when edge quality or safety is insufficient.

## Implemented no-trade triggers

### N1 - No setup candidate
- Source: `pipeline.py`
- Condition: no tradable setups after analysis/filtering.

### N2 - Playbook rejection
- Source: `risk_engine.py::filter_setups_by_playbook`
- Condition: not in allowlist, in denylist, or kill-switched.

### N3 - Daily and run lockouts
- Source: `risk_engine.py::check_daily_limits/check_circuit_breakers`
- Condition: day stop, run stop, cap reached.

### N4 - Cooldown/session lock
- Source: `risk_engine.py::check_cooldown_and_session_limit`
- Condition: playbook/session anti-spam rules violated.

### N5 - Sizing invalid
- Source: `risk_engine.py::calculate_position_size`
- Condition: invalid stop distance, insufficient size/capital constraints.

### N6 - Execution refusal
- Source: `paper_trading.py::place_order`
- Condition: limits fail at execution-time check.

## Canon extension (required but partly missing)
- News conflict no-trade policy: currently partial and playbook-dependent.
- Data-feed health no-trade policy: not yet explicit as first-class reject reason.
- Reconciliation no-trade policy for live mode: not yet implemented.

