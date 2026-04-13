# Phase 4 — Audit D27 / funnel (`labfull_202511`)

**Date :** 2026-04-11  
**Source de vérité :** `backend/results/labs/full_playbooks_24m/debug_counts_labfull_202511.json` (`counts.*`).

---

## PREUVE CODE

Pas de nouveau code : classification dérivée des champs :

- `matches_by_playbook` → **M**
- `setups_created_by_playbook` → **S**
- `setups_after_risk_filter_by_playbook` → **SR**
- `trades_opened_by_playbook` → **T**
- `setups_rejected_by_mode_by_playbook` + `setups_rejected_by_mode_examples` → **BLOCKED_BY_POLICY** (DENYLIST / mode)

---

## PREUVE RUN

Run : `labfull_202511`, config dans le JSON (`start_date` 2025-11-01, `end_date` 2025-11-30, SPY+QQQ, AGGRESSIVE).

Totaux extraits :

- `playbooks_registered_count` = **13**
- `matches_total` = **9699**
- `setups_created_total` = **7363**
- `setups_after_risk_filter_total` = **3653**
- `setups_rejected_by_mode` = **756**
- `trades_opened_total` = **1634**

---

## PREUVE TEST

N/A (audit sur artefact JSON). La cohérence table ↔ JSON est vérifiable par :

```bash
python3 -c "import json; d=json.load(open('results/labs/full_playbooks_24m/debug_counts_labfull_202511.json'))['counts']; print(d['trades_opened_by_playbook'])"
```
(depuis `backend/`, chemins adaptés)

---

## Table M / S / SR / T (13 playbooks)

| Playbook | M | S | SR | T |
|----------|--:|--:|--:|--:|
| NY_Open_Reversal | 579 | 436 | 436 | 43 |
| Liquidity_Sweep_Scalp | 1500 | 1085 | 1085 | 863 |
| Morning_Trap_Reversal | 1924 | 1417 | 1417 | 369 |
| Trend_Continuation_FVG_Retest | 440 | 440 | 440 | 249 |
| FVG_Fill_Scalp | 236 | 236 | 236 | 71 |
| Session_Open_Scalp | 61 | 39 | 39 | 39 |
| London_Sweep_NY_Continuation | 580 | 580 | 0 | 0 |
| BOS_Momentum_Scalp | 196 | 196 | 0 | 0 |
| DAY_Aplus_1_Liquidity_Sweep_OB_Retest | 1957 | 1373 | 0 | 0 |
| SCALP_Aplus_1_Mini_FVG_Retest_NY_Open | 2226 | 1561 | 0 | 0 |
| News_Fade | 0 | 0 | 0 | 0 |
| Power_Hour_Expansion | 0 | 0 | 0 | 0 |
| Lunch_Range_Scalp | 0 | 0 | 0 | 0 |

---

## Classifieur (taxonomie demandée)

| Classe | Critère (ce run) | Playbooks |
|--------|------------------|-----------|
| **TRADED** | T > 0 | NY_Open_Reversal, Liquidity_Sweep_Scalp, Morning_Trap_Reversal, Trend_Continuation_FVG_Retest, FVG_Fill_Scalp, Session_Open_Scalp |
| **BLOCKED_BY_POLICY** | S > 0, SR = 0, rejet mode (DENYLIST) | London_Sweep_NY_Continuation, BOS_Momentum_Scalp, DAY_Aplus_1_*, SCALP_Aplus_1_* |
| **MATCH_ONLY** | M > 0, S = 0 | *aucun* parmi les 13 |
| **SETUP_ONLY** | S > 0, SR > 0, T = 0 | *aucun* parmi les 13 |
| **DEAD** | M = 0 (pas de ligne dans `matches_by_playbook`) | News_Fade, Power_Hour_Expansion, Lunch_Range_Scalp |

**Goulot d’étranglement SR → T** (sélection / caps / exécution), pour les **TRADED** :

| Playbook | SR − T |
|----------|--------:|
| NY_Open_Reversal | 393 |
| Liquidity_Sweep_Scalp | 222 |
| Morning_Trap_Reversal | 1048 |
| Trend_Continuation_FVG_Retest | 191 |
| FVG_Fill_Scalp | 165 |
| Session_Open_Scalp | 0 |

---

## ANALYSE

- L’ancienne table dans `D27_PORTFOLIO_AUDIT_labfull_202511.md` mélangeait des playbooks **non chargés** dans ce run et des chiffres **non issus** de ce `debug_counts` — **corrigé** pour ne garder que les **13** enregistrés.
- **News_Fade** n’a **aucun** match sur nov 2025 dans cet artefact : toute narrative « 1 setup SR » pour ce mois est **fausse** pour ce fichier.

---

## DÉCISION

| Élément | Verdict |
|---------|---------|
| Artefact `debug_counts_labfull_202511.json` | **KEEP** comme référence D27 pour ce run |
| Doc D27 | **FIX** (alignement sections 1–2–4 + §3) |
| Phase 4 | **DONE** pour cette fenêtre |

---

## NEXT STEP

- **Phase 5 (SAFE)** : scorer **NY_Open_Reversal** + **Session_Open_Scalp** (conversion SR→T complète) sur critères perf (autre JSON / parquet trades) ; **News_Fade** = run avec événements news ou autre mois.
- **Phase 6** : réactiver playbook **policy-blocked** uniquement via allowlist + lab isolé (ne pas toucher NY pipeline).

---

## Mise à jour du pointeur phases 4–8

Voir `PHASES_4_8_POINTER.md` : Phase 4 réalisée sur `labfull_202511` ; phases 5–8 toujours ouvertes.
