# ASSUMPTIONS (Phase 1-2)

## Proven assumptions (high confidence)
1. Primary runtime is Python/FastAPI with a trading and backtest API surface.
2. Core tradable universe in current implementation is SPY/QQQ.
3. Backtests are job-based and persist artifacts under `backend/results/`.
4. Paper trading uses local simulation (`ExecutionEngine`), not broker fills.

## Working assumptions (medium confidence)
1. `MASTER_FINAL.txt` is a concatenated corpus source containing mixed-quality transcripts.
2. `playbooks_Aplus_from_transcripts.yaml` is intended as transcript-derived strategy extraction, but not yet system-wide canonical source.
3. AGGRESSIVE backtest mode currently serves both trading simulation and calibration/audit workflows (with selective bypasses in evaluator logic).

## Unproven assumptions (must be validated)
1. Full intended corpus list from product brief is available in workspace.
2. Existing backtest outputs are representative for multi-regime robustness.
3. Daily-bias methodology in corpus is fully and faithfully encoded end-to-end.
4. Live IBKR path can be activated safely without additional adapter work.

## Assumption policy
- Any unproven assumption must stay marked in docs and must not be treated as implementation truth.
- If code and corpus disagree, code behavior is truth for current-state mapping; discrepancy is logged as gap.

