# OPEN QUESTIONS (Phase 1)

## Corpus availability and quality
1. Where are these expected files in this workspace?
   - `How To Find Daily Bias (Step By Step)-e_FV0Q14k8E.txt`
   - `How_To_Start_Day_Trading_As_A_Beginner_In_2025_9_hours-[aobHuNcI1QM].txt`
   - `The Trading Industry Will Hate Me for This FREE 10+ Hour Course-grw58BIzotU.txt`
   - candlestick/breakout PDFs
2. Is `data/MASTER_FINAL.txt` a curated canonical corpus or a raw dump that needs filtering before rule extraction?

## Strategy canon decisions
3. Should `setup_engine_v2 + playbook_loader` be the single canonical strategy path, with `setup_engine.py` considered legacy?
4. Which session-profile logic is authoritative when code and transcript text differ?
5. Which no-trade rules are mandatory for production gate vs optional research filters?

## Validation and lifecycle gates
6. What is the required paper-trading gate before live (duration, min trades, max DD, PF threshold)?
7. What is the required out-of-sample and walk-forward protocol before strategy promotion?

## Live execution
8. Is the target live rollout strictly smallest-size-first with hard freeze on any reconciliation mismatch?
9. Which broker events must trigger immediate kill-switch (disconnect duration, order reject type, stale positions)?

## Data integrity
10. Which data provider(s) are approved for production backtest datasets, and what normalization policy is required (splits/dividends/session calendar)?

