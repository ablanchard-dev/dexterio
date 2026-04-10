# Baseline EDGE State (figée)

Date baseline: 2026-04-09

## Décisions de policy

- `NY_Open_Reversal`: **edge survivant** (actif, logique métier inchangée).
- `Session_Open_Scalp`: **LAB ONLY / bloqué runtime edge**.
- `Trend_Continuation_FVG_Retest`: **quarantaine** (non réactivé).

## État technique validé

- Invariants de run: `sanity_report` / `post_run_verification` / `structural_diagnostics` / `grading_debug` / `master_candle_debug` / exports trades parquet+csv.
- Filtres edge non-NY en place:
  - rejet `regime_chop`
  - rejet `no_liquidity_event`
  - rejet `rr_too_low`

## Runs de référence à conserver

- Référence courte historique: `ref_validation_20260409` (SPY, 2025-08-04..2025-08-08).
- Référence labo 1 mois: `labfull_202511` (SPY+QQQ, allowlists respectées).

## Artefacts de référence à relire

Sous `backend/results/labs/full_playbooks_24m/`:

- `summary_labfull_202511_AGGRESSIVE_DAILY_SCALP.json`
- `sanity_report_labfull_202511.json`
- `post_run_verification_labfull_202511.json`
- `structural_diagnostics_labfull_202511.json`
- `lab_playbook_comparison_labfull_202511.json`
- `trades_labfull_202511_AGGRESSIVE_DAILY_SCALP.parquet`
- `debug_counts_labfull_202511.json`

## Commandes de rerun de référence

Depuis la racine repo:

```powershell
python "backend/scripts/run_full_playbooks_lab.py" --months 1 --symbols SPY,QQQ --respect-allowlists --anchor-end 2025-11-30
```

Run court SPY (validation locale):

```powershell
python "backend/scripts/run_backtest_verify.py"
```
