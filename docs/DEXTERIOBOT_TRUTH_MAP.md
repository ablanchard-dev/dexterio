# DEXTERIOBOT Truth Map (Phase 1)

## Scope and method
- This map is repo-first: code behavior is treated as primary truth.
- Corpus files are used only where physically present in this workspace.
- Each claim is tagged as **Proven**, **Partial**, or **Unproven**.

## What the system is today (proven)

### 1) Product identity
- **Proven**: DexterioBot is implemented as a trading system (not a coaching chatbot).
  - Evidence: `backend/engines/pipeline.py`, `backend/backtest/engine.py`, `backend/routes/trading.py`, `backend/routes/backtests.py`.

### 2) Lifecycle components present
- **Proven**: Strategy extraction from playbooks exists in code form.
  - Evidence: `backend/engines/playbook_loader.py`, `backend/engines/setup_engine_v2.py`, `backend/knowledge/playbooks.yml`, `backend/knowledge/aplus_setups.yml`.
- **Proven**: Backtesting engine exists with replay and metrics.
  - Evidence: `backend/backtest/engine.py`, `backend/models/backtest.py`.
- **Proven**: Paper trading loop exists.
  - Evidence: `backend/engines/execution/paper_trading.py`, `backend/services/bot_scheduler.py`, `backend/routes/trading.py`.
- **Partial**: Live IBKR execution is not fully wired for order routing.
  - Evidence: `backend/engines/execution/ibkr_gateway.py` only checks connectivity; `routes/trading.py` includes explicit warning about remaining routing work.

### 3) Core trading pipeline
- **Proven**: Multi-step pipeline is implemented:
  - data -> market state -> liquidity -> patterns -> playbook matching -> setup scoring -> risk -> execution.
  - Evidence: `backend/engines/pipeline.py`.

### 4) Bias and session logic
- **Proven**: HTF structure and bias are computed from daily/h4/h1.
  - Evidence: `backend/engines/market_state.py`.
- **Partial**: Session-profile model exists, but with defaults/placeholders in live calls.
  - Evidence: `classify_session_profile()` in `market_state.py`; hardcoded sample input in `create_market_state()`.

### 5) Setup and confluence logic
- **Proven**: Setup scoring and quality grades exist (A+/A/B/C).
  - Evidence: `backend/engines/setup_engine.py`, `backend/models/setup.py`.
- **Proven**: Playbook-driven setup generation (V2) exists.
  - Evidence: `backend/engines/setup_engine_v2.py`, `backend/engines/playbook_loader.py`.
- **Partial**: Some criteria are relaxed in AGGRESSIVE backtest mode to avoid over-filtering while engines are incomplete.
  - Evidence: `is_backtest_aggressive` bypasses in `playbook_loader.py`.

### 6) Risk controls
- **Proven**: Risk engine includes allowlist/denylist, cooldown caps, daily/run circuit breakers, 2R/1R state machine.
  - Evidence: `backend/engines/risk_engine.py`, `backend/models/risk.py`.
- **Proven**: No-trade outputs are supported by rejection paths.
  - Evidence: `can_take_setup()`, `check_daily_limits()`, `filter_setups_by_playbook()` in `risk_engine.py`.

### 7) Backtest fidelity
- **Proven**: Costs/slippage/spread/commission model exists.
  - Evidence: `backend/models/backtest.py`, `backend/backtest/costs.py`, usage in `backtest/engine.py`.
- **Proven**: Anti-lookahead intent exists via chronological replay.
  - Evidence: architecture comments and minute driver in `backtest/engine.py`.
- **Partial**: Walk-forward and robust OOS orchestration are not first-class APIs yet.
  - Evidence: no dedicated walk-forward module in current tree.

### 8) Paper and runtime ops
- **Proven**: Async loop can start/stop and update positions continuously.
  - Evidence: `backend/services/bot_scheduler.py`, `/trading/control` in `backend/routes/trading.py`.
- **Proven**: Journaling and KPI computation exist.
  - Evidence: `backend/engines/journal.py`.

### 9) Security baseline
- **Proven**: API-key protection for backtests and trading routes.
  - Evidence: `backend/security/api_key.py`, route dependencies in `routes/backtests.py` and `routes/trading.py`.
- **Proven**: secure file and job-id validation.
  - Evidence: `backend/security/validation.py`.

## Canonical vs messy areas
- **Canonical (strong)**: risk constraints, backtest job system, router structure, playbook loading framework.
- **Messy / mixed maturity**:
  - old and new setup paths coexist (`setup_engine.py` and `setup_engine_v2.py`);
  - some market-state/session inputs are placeholder-like;
  - corpus-to-rule provenance is incomplete due missing files in workspace.

## Current gates (as-implemented)
1. Setup must pass playbook and mode filters.
2. Setup must pass risk checks (daily limits, caps, kill-switch, cooldown).
3. Backtest jobs are constrained by API validations and run-state.
4. Live mode start checks IBKR connectivity when configured.

## Principal gaps against strict V2 target
- Missing/partial source corpus in repo prevents full canonical extraction from transcripts.
- Live execution adapter is not yet complete order-routing logic.
- No explicit centralized "paper-to-live gate policy" document in codebase.
- No dedicated strategy-compiler artifact format yet (rules JSON/YAML produced from corpus extraction pipeline).

