# BOUNDARIES

## Product boundaries (non-negotiable)
- DexterioBot is a market-facing trading system.
- Psychology is allowed only as operational constraints (cooldown, lockouts, discipline tags), not as coaching persona.
- No "dashboard theater" without trading logic evidence.

## Engineering boundaries
- Prefer improving existing modules over rewriting:
  - pipeline, setup/risk engines, backtest engine, paper loop.
- Any new rule must have source provenance (code or corpus excerpt).
- No live-order implementation before backtest/paper gates are documented and satisfied.

## Data and reproducibility boundaries
- No hidden spreadsheet/manual logic in core decision path.
- Backtest assumptions (costs, spread, slippage) must be explicit and versioned.
- Outputs must be reproducible from config + data path + code version.

## Safety boundaries
- Hard rejection is valid output (no-trade) and must be preserved.
- Risk controls cannot be bypassed in production mode.
- Emergency stop behavior must remain available regardless of UI state.

## Scope boundaries for Phase 1-2
- Deliver docs and truth mapping only (no strategy rewrite and no live-order routing changes in this phase).

