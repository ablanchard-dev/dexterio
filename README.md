# DexterioBOT

A **backtesting and strategy-research platform** for US index futures / ETFs
(SPY, QQQ and others), built around one principle: **prove an edge with rigorous,
honest testing before trusting it** — and archive it cleanly when it fails.

> ⚠️ **Status: research.** This is not a live or profitable trading system. Its value
> is the engineering and the methodology: a disciplined pipeline that tested ~20
> families of strategies and **falsified all of them** with proper statistical tests.
> That negative result is documented on purpose — avoiding self-deception *is* the point.

## What it does

- **Backtest engine** — bar-by-bar simulation with realistic execution: intrabar
  stop/take-profit priority, trailing stops, break-even logic, time stops, and a
  pluggable **fill model** (ideal vs conservative with slippage + spread) so paper
  results can be reconciled against a realistic baseline.
- **Strategy definitions as data** — strategies ("playbooks") are described in YAML and
  loaded by the engine, so new ideas can be added without touching the core.
- **Rigorous validation** — every strategy is judged on **expectancy per trade**, with
  walk-forward / out-of-sample windows, and **permutation tests** to check that results
  aren't just luck. Strategies that look good in-sample but fail a permutation test are
  archived, not shipped.
- **Full-stack** — Python/FastAPI backend with a React frontend for running and
  inspecting backtest campaigns.

## What I learned building it

Across ~20 strategy families (pattern-based, momentum, mean-reversion, stat-arb,
event-driven, cross-asset), **none produced a robust edge** on free retail data for
liquid US/crypto markets. Each was killed by a pre-written rule, not by wishful
re-interpretation. The real deliverable is the **research discipline**: pre-registered
hypotheses, pre-written kill rules, honest statistics, and reusable infrastructure.

## Stack

`Python` · `FastAPI` · `React` · `numpy` / `pandas` · `pytest` · `yfinance` ·
YAML-driven strategy config

## Run (dev)

```bash
# Backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.server:app --reload

# Frontend
cd frontend && npm install && npm start
```

## Repository layout

```
backend/
├── engines/        # backtest engine, execution, fill models, pattern detectors
├── backtest/        # campaign runner
├── knowledge/       # YAML strategy definitions & campaigns
├── scripts/         # research / audit scripts (one-off analyses)
└── docs/            # methodology, roadmaps, verdicts
frontend/            # React UI
```

---

*Solo project — autodidact. The interesting part is the methodology, not a P&L curve.*
