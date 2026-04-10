# SOURCE PROVENANCE (Phase 2)

## A. Source-of-truth hierarchy applied
1. existing code behavior
2. existing bot logic/services/routes
3. corpus text files present in workspace
4. docs and logs

## B. Corpus inventory status

### Present
- `data/MASTER_FINAL.txt` (very large, mixed transcript dump)
- `backend/knowledge/playbooks_Aplus_from_transcripts.yaml` (structured transcript-derived rules)

### Missing from workspace (searched, not found)
- `How To Find Daily Bias (Step By Step)-e_FV0Q14k8E.txt`
- `How_To_Start_Day_Trading_As_A_Beginner_In_2025_9_hours-[aobHuNcI1QM].txt`
- `The Trading Industry Will Hate Me for This FREE 10+ Hour Course-grw58BIzotU.txt`
- Candlestick/breakout PDFs

## C. Rule provenance matrix (sample canonical rules)

| Rule ID | Source file(s) | Evidence anchor | Confidence | Ambiguity |
|---|---|---|---|---|
| C1 Pipeline stages | `backend/engines/pipeline.py` | `run_full_analysis()` ordered stages | High | No |
| C2 Playbook schema | `backend/knowledge/playbooks.yml` | `timefilters/context/ict/candles/scoring` blocks | High | Low |
| C3 A+ setup ingestion | `backend/knowledge/aplus_setups.yml`, `backend/engines/playbook_loader.py` | conversion path into playbook definitions | High | Low |
| C4 Risk authority | `backend/engines/risk_engine.py` | allow/deny, caps, cooldown, breakers | High | No |
| C5 Backtest realism | `backend/models/backtest.py`, `backend/backtest/engine.py` | cost fields + replay engine | High | Low |
| C6 Paper loop | `backend/services/bot_scheduler.py` | periodic execute/update loop | High | No |
| C7 Live status gap | `backend/engines/execution/ibkr_gateway.py`, `backend/routes/trading.py` | connectivity check + warning on routing not complete | High | No |
| C8 Bias/profile model | `backend/engines/market_state.py` | bias voting + profile classifier | Medium | Yes |

## D. Corpus-to-code alignment notes
- Transcript-derived playbooks exist (`playbooks_Aplus_from_transcripts.yaml`) but are not the only active strategy source.
- Active runtime strategy path is currently code + YAML playbook config (`playbooks.yml`, `aplus_setups.yml`), then evaluator.
- Any claim requiring missing files remains marked unresolved until files are provided.

