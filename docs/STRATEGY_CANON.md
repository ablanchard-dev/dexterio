# STRATEGY CANON (Phase 2 draft)

This canon is constrained to evidence available in current repo and corpus files present in workspace.

## Canon rule format
- **Source**: file path
- **Excerpt/anchor**: function or section
- **Interpretation**: machine-usable meaning
- **Confidence**: high/medium/low
- **Ambiguity**: yes/no

## Canonical rule set

### Rule C1 - Multi-stage decision pipeline
- Source: `backend/engines/pipeline.py`
- Excerpt: `run_full_analysis()`
- Interpretation: every setup candidate must pass ordered stages (data, state, liquidity, patterns, playbook, scoring, mode filter).
- Confidence: high
- Ambiguity: no

### Rule C2 - Setup quality grading
- Source: `backend/engines/setup_engine.py`, `backend/engines/setup_engine_v2.py`
- Excerpt: score thresholds and match grade propagation
- Interpretation: setup grade classes A+/A/B/C are explicit and feed execution eligibility.
- Confidence: high
- Ambiguity: low (dual engine path still coexists)

### Rule C3 - Playbook-first strategy expression
- Source: `backend/engines/playbook_loader.py`, `backend/knowledge/playbooks.yml`, `backend/knowledge/aplus_setups.yml`
- Interpretation: strategy logic is represented as declarative playbooks with context/time/ICT/candle/entry/SL/TP/scoring.
- Confidence: high
- Ambiguity: medium (some fields are placeholder or relaxed in aggressive backtest mode)

### Rule C4 - Risk authority
- Source: `backend/engines/risk_engine.py`
- Interpretation: risk engine is final authority for allow/deny (allowlist, denylist, cooldown, caps, kill-switch, daily limits).
- Confidence: high
- Ambiguity: no

### Rule C5 - No-trade is first-class output
- Source: `risk_engine.py`, `pipeline.py`, `routes/trading.py`
- Interpretation: invalid setup, poor context, limits reached, or risk failure must produce no-trade / rejection.
- Confidence: high
- Ambiguity: no

### Rule C6 - Backtest realism controls
- Source: `backend/models/backtest.py`, `backend/backtest/engine.py`
- Interpretation: commissions, spread, slippage, timestamps, and risk lifecycle are modeled as part of result credibility.
- Confidence: high
- Ambiguity: low

### Rule C7 - Paper before live behavior
- Source: `backend/services/bot_scheduler.py`, `backend/routes/trading.py`, `backend/engines/execution/ibkr_gateway.py`
- Interpretation: runtime loop exists for paper; live IBKR currently has connectivity gate but incomplete order-routing adapter.
- Confidence: high
- Ambiguity: no

## Canonical non-goals
- No motivational/coach persona logic in signal path.
- No strategy invention without provenance.
- No live execution trust without passing backtest + paper gates.

