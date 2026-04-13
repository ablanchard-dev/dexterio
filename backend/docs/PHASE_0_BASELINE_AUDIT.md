# Phase 0 — Baseline & sanity (PREUVE)

**Date (workspace) :** 2026-04-11  
**Objectif :** valider le runner canonique, l’absence de pollution « fake setup », comparer `labfull_202511` vs `job_*`, trancher **13 vs 27** playbooks.

---

## PREUVE CODE

### Runner lab « canonique »

`backend/scripts/run_full_playbooks_lab.py` écrit explicitement dans le meta de fenêtre :

- `"runner": "run_full_playbooks_lab.py"`
- `"protocol": "CANONICAL_LAB"`

(voir métadonnées autour des lignes 107–109 du script.)

### Comptage `playbooks_registered_count`

Dans `backend/backtest/engine.py`, au init du moteur :

- `all_playbooks = list(core) + list(aplus)` (loader YAML core + entrées A+)
- `playbooks_registered_count = len(all_playbooks)` (pas un filtre risk à ce stade)

### Fake setup

`backend/backtest/engine.py` : déclenchement **uniquement** si  
`BACKTEST_ENABLE_FAKE_SETUP_TRIGGER` ∈ `{1, true, yes, on}` ; sinon aucune injection.

### Inventaire YAML (dépôt actuel)

- `backend/knowledge/playbooks.yml` : **11** clés `playbook_name:` (grep dépôt).
- Les 2 playbooks A+ visibles dans les runs : `DAY_Aplus_1_*`, `SCALP_Aplus_1_*` → **11 + 2 = 13** attendus pour `playbooks_registered_count`.

### Écart historique 27

`backend/results/labs/full_playbooks_24m/inventory_audit_labfull_202511_vs_202510.json` :

- `runtime_counts.playbooks_registered_count`: **13** (202511)
- `reference_counts.playbooks_registered_count`: **27** (202510)
- `missing_vs_reference` : **14** noms absents du runtime actuel vs référence (ex. `NY_Lunch_Breakout_Reprice`, `VWAP_Reclaim_Trend_Day`, …).

---

## PREUVE RUN

| Artefact | `playbooks_registered_count` | Liste alignée |
|----------|------------------------------|---------------|
| `backend/results/labs/full_playbooks_24m/debug_counts_labfull_202511.json` | **13** | Identique à `playbooks_registered_names` |
| `backend/results/jobs/16096260/debug_counts.json` (`job_*`) | **13** | Même liste de 13 noms |

**Tentative locale :** import `engines.playbook_loader` via `python3` a échoué (`ModuleNotFoundError: yfinance`) — l’environnement du workspace n’a pas les deps backend ; la preuve runtime du **loader seul** n’a pas été rejouée ici. Les JSON ci-dessus restent la preuve d’exécution passée cohérente avec le YAML actuel.

**Cas 27 dans le repo :** présents dans certains `backend/results/ref_runs/*.json` et validations kill-switch — **runs/configs historiques ou chemins différents**, pas contradiction avec le dépôt YAML actuel + `debug_counts_labfull_202511.json`.

---

## PREUVE TEST

- Aucune suite de tests relancée pour cette phase (scope baseline uniquement ; deps Python incomplètes sur la machine d’audit).

---

## ANALYSE

1. **Baseline « 27 playbooks chargés »** : **fausse pour le code + données actuels** ; la cible **27** correspond à un **état antérieur** (cf. `labfull_202510` / `inventory_audit`), pas au `playbooks.yml` actuel (11 core).
2. **`labfull_202511` vs `job_*`** : **cohérents** sur **13** playbooks enregistrés et la même liste de noms (ex. `job_16096260`).
3. **Anomalie critique documentaire :** `backend/docs/D27_PORTFOLIO_AUDIT_labfull_202511.md` affirmait **27** `playbooks_registered_count` — **en contradiction directe** avec `debug_counts_labfull_202511.json` (**13**). Correction alignée sur les artefacts (voir commit / diff doc).

---

## DÉCISION

| Élément | Verdict |
|---------|---------|
| Runner canonique lab | **KEEP** — `run_full_playbooks_lab.py` + `CANONICAL_LAB` |
| Pollution fake setup | **KEEP** — opt-in env uniquement |
| Cible 27 playbooks (runtime actuel) | **FIX** (Phase 2) — soit restaurer les playbooks manquants dans YAML/sources, soit réviser la cible produit (13 documentés) |
| Doc D27 « 27 enregistrés » | **FIX** — aligner sur **13** + pointer l’audit inventaire |

**Rollback :** aucun changement de logique moteur ; uniquement doc + ce fichier d’audit.

---

## NEXT STEP

- **Phase 1** — Data / candles / ingestion (timezone, trous, OHLC, multi-TF), comme planifié.
- En parallèle logique **Phase 2** : inventaire YAML ↔ loader ↔ `debug_counts` pour décider si les **14** playbooks listés dans `inventory_audit`… doivent réintégrer `playbooks.yml` (ou fichier dédié) pour retrouver une cible **27** si c’est toujours l’objectif produit.
