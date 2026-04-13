# Phase 2 — Inventaire playbooks (PREUVE)

**Date :** 2026-04-11

---

## PREUVE CODE — Sources YAML

| Source | Rôle | Chargé par `PlaybookLoader` ? |
|--------|------|-------------------------------|
| `backend/knowledge/playbooks.yml` | Playbooks **CORE** | **Oui** (liste racine YAML) |
| `backend/knowledge/aplus_setups.yml` | DAY / SCALP **A+** | **Oui** → `aplus_playbooks` |
| `backend/knowledge/paper_wave1_playbooks.yaml` | Allowlist **paper Wave 1** | **Non** (consommé par `RiskEngine._load_paper_wave1_allowlist` si `PAPER_USE_WAVE1_PLAYBOOKS`) |
| `backend/knowledge/playbooks_Aplus_from_transcripts.yaml` | Brouillons / transcripts | **Non** (pas référencé dans `playbook_loader.py`) |

**Comptage CORE (grep dépôt) :** **11** entrées `- playbook_name:` dans `playbooks.yml`.  
**A+ :** **2** noms (`DAY_Aplus_1_Liquidity_Sweep_OB_Retest`, `SCALP_Aplus_1_Mini_FVG_Retest_NY_Open`).

**Runtime attendu :** `playbooks_registered_count` = **13** = `len(core) + len(aplus)` dans `backtest/engine.py` (init moteur).

---

## PREUVE RUN / ARTEFACTS

- `backend/results/labs/full_playbooks_24m/debug_counts_labfull_202511.json` → **13** enregistrés (aligné YAML actuel).
- `backend/results/labs/full_playbooks_24m/inventory_audit_labfull_202511_vs_202510.json` :
  - `source_counts`: core **11**, aplus **2**, total **13**
  - `missing_vs_reference` : **14** noms présents dans la baseline **202510** mais absents du loader actuel (ex. `VWAP_Reclaim_Trend_Day`, `NY_Lunch_Breakout_Reprice`, …).

---

## CLASSIFICATION (état dépôt actuel)

### ACTIVE (chargés = éligibles matching/setup côté loader)

Les **13** noms listés dans `playbooks_registered_names` de `debug_counts_labfull_202511.json` :

NY_Open_Reversal, London_Sweep_NY_Continuation, Trend_Continuation_FVG_Retest, Morning_Trap_Reversal, Power_Hour_Expansion, News_Fade, Liquidity_Sweep_Scalp, FVG_Fill_Scalp, BOS_Momentum_Scalp, Session_Open_Scalp, Lunch_Range_Scalp, DAY_Aplus_1_Liquidity_Sweep_OB_Retest, SCALP_Aplus_1_Mini_FVG_Retest_NY_Open.

### MISSING (référence historique 27 − 13)

Les **14** chaînes de `missing_vs_reference` dans `inventory_audit_labfull_202511_vs_202510.json` — **à réintégrer dans YAML (ou source dédiée)** si l’objectif produit reste **27** playbooks CORE.

### DEAD (fichiers non branchés au loader)

- Entrées dans `playbooks_Aplus_from_transcripts.yaml` (schéma narratif, pas merge dans `PlaybookDefinition`).

### POLICY (pas « mort », mais hors loader)

- `paper_wave1_playbooks.yaml` : **3** noms (NY_Open_Reversal, News_Fade, Liquidity_Sweep_Scalp) — filtre **risk/paper**, pas inventaire loader.

---

## ANALYSE

- L’écart **13 vs 27** n’est **pas** un bug de comptage runtime : il reflète un **YAML allégé** vs run `labfull_202510`.
- `playbook_quarantine.yaml` agit en **policy** (deny/quarantine) ; orthogonal au nombre d’objets chargés depuis YAML.

---

## DÉCISION

| Sujet | Verdict |
|--------|---------|
| Loader | **KEEP** (cohérent avec fichiers actuels) |
| Cible 27 | **FIX** produit : réintroduire ou sourcer les **14** manquants **ou** abaisser la cible documentée |
| `playbooks_Aplus_from_transcripts.yaml` | **Hors scope** tant non branché — **DEAD** pour l’exécution |

---

## NEXT STEP

- Décision produit : restaurer les 14 playbooks dans `playbooks.yml` (ou fichier secondaire + merge loader **minimal** si tu veux isoler).
- Phase 3 : exécution réaliste (déjà codée pour Wave 1 — voir `PHASE_3_VALIDATION_3B.md`).
