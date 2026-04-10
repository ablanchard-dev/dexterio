# Backtesting Plan (Gate 3)

## Scope
- Exécuter un labo **full-playbooks** sur horizon `last_24m`.
- Utiliser des fenêtres rolling mensuelles pour limiter le hasard d'une fenêtre unique.
- Produire des artefacts consolidés pour ranking agressif.

## Procédure
- Lancer le runner: `python backend/scripts/run_full_playbooks_lab.py --months 24 --top-n 8`.
- Le runner active uniquement pour ce contexte:
  - `RISK_EVAL_ALLOW_ALL_PLAYBOOKS=true`
  - `RISK_EVAL_RELAX_CAPS=true`
  - `RISK_EVAL_DISABLE_KILL_SWITCH=true`
- Les artefacts sont écrits dans `backend/results/labs/full_playbooks_24m`.

## Artefacts attendus
- `lab_windows_index.json` (index des runs/fenêtres).
- `playbook_stats_labfull_YYYYMM.json` par fenêtre.
- `summary_labfull_YYYYMM_*.json` par fenêtre.

## Contrôles minimum
- Aucune fenêtre sans `playbook_stats`.
- Cohérence période index (`start/end`) vs runs générés.
- Reproductibilité: même entrée => même ranking (ordre stable par métriques).

