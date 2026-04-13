# Phases 4 à 8 — Pointeur (pas d’exécution dans ce lot)

**Date :** 2026-04-11

Les phases **1–3** ont été traitées avec preuves dans :

- `PHASE_1_DATA_AUDIT.md`
- `PHASE_2_PLAYBOOK_INVENTORY.md`
- `PHASE_3_VALIDATION_3B.md`
- `PHASE_0_BASELINE_AUDIT.md` (référence baseline)

## Phase 4 — Audit D27 (portfolio)

**Fait (2026-04-11) :** `PHASE_4_D27_FUNNEL_labfull_202511.md` + correction de `D27_PORTFOLIO_AUDIT_labfull_202511.md` (13 playbooks, chiffres = `debug_counts_labfull_202511.json`).

**Artefacts :**

- `backend/results/labs/full_playbooks_24m/debug_counts_labfull_202511.json`
- `backend/results/labs/full_playbooks_24m/inventory_audit_labfull_202511_vs_202510.json` (comparatif 13 vs 27 historique)

**Si nouveau run :** régénérer le funnel à partir du nouveau `debug_counts_*.json`.

## Phase 5 — SAFE (4–5 snipers)

**Fait (2026-04-11) :** métriques parquet → `PHASE_5_SAFE_MODE_PARQUET_PROOF.md` (nov 2025 : **aucun** candidat SAFE « elite » validé sur ce seul mois).

## Phase 6 — FULL (expansion)

**Fait (2026-04-11) :** principes et ordre d’attaque → `PHASE_6_FULL_MODE.md` (pas de changement allowlist dans le code sur ce passage).

## Phase 7 — Refine playbooks (contexte mesurable)

**Fait (2026-04-11) :** volatilité 1m + propagation `day_type` / `volatility` vers l’évaluateur — voir `PHASE_7_8_IMPLEMENTATION.md`.

## Phase 8 — Robustesse prod (coûts)

**Fait (2026-04-11) :** tests `tests/test_backtest_costs.py` sur `backtest/costs.py` — voir `PHASE_7_8_IMPLEMENTATION.md`.

---

**DÉCISION :** Phases **4–8** couvertes (docs +, pour 7–8, patch minimal + tests).
