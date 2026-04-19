# Phase A — Fair Audit 4-Weeks Verdict

**Date** : 2026-04-19
**Scope** : Fair audit jun_w3 + aug_w3 + oct_w2 + nov_w4 × SPY + QQQ, env flags `RISK_EVAL_ALLOW_ALL_PLAYBOOKS=true RISK_EVAL_RELAX_CAPS=true RISK_EVAL_DISABLE_KILL_SWITCH=true` (denylist + caps + kill-switch bypassés).
**Artefacts** :
- [VERDICT_fair_audit_4weeks.md](../results/labs/mini_week/VERDICT_fair_audit_4weeks.md) (table complète)
- `backend/results/labs/mini_week/fair_{jun_w3, aug_w3, oct_w2, nov_w4}/`
- Scripts : [analyze_fair_audit.py](../scripts/analyze_fair_audit.py), [build_experiment_index.py](../scripts/build_experiment_index.py)

---

## Résumé exécutif

- **5249 trades** sur 4 semaines, total_R = **-568.10**, E[R] = **-0.1082**.
- **17/28 playbooks** registered ont fire au moins une fois.
- **13/28** atteignent ≥5 trades sur 4 semaines (gate "≥20/28" formellement FAIL).
- **11 playbooks silencieux** (zéro matches même avec risk filter bypassed) — dont **6/7 MASTER faithful**.

## Verdict par playbook (classification)

### KILL (3, trades ≥ 15 & E[R] < -0.1)

| Playbook | Trades | E[R] | WR | total_R | Commentaire |
|----------|--------|------|----|---------|-------------|
| DAY_Aplus_1_Liquidity_Sweep_OB_Retest | 2157 | -0.1993 | 17.0% | -429.94 | Déjà DENYLIST. Signal spam confirmé. |
| NY_Open_Reversal | 17 | -0.2106 | 11.8% | -3.58 | **Contredit CLAUDE.md "only legacy non-négatif"**. À sortir de AGGRESSIVE_ALLOWLIST. |
| ORB_Breakout_5m | 16 | -0.1025 | 25.0% | -1.64 | Trop tôt pour calibrer. À sortir de AGGRESSIVE_ALLOWLIST. |

### CALIBRATE (5, trades ≥ 15 & -0.1 ≤ E[R] ≤ 0.15 & avg|mae_r| > 0.3)

| Playbook | Trades | E[R] | avg_peak_R | time_stop % | Commentaire |
|----------|--------|------|------------|-------------|-------------|
| Engulfing_Bar_V056 | 26 | +0.0021 | 0.643 | 50% | Près breakeven, petit ajustement |
| BOS_Scalp_1m | 42 | -0.0056 | 0.360 | 57% | Time-stop dominant |
| Liquidity_Sweep_Scalp | 39 | -0.0429 | 0.438 | 69% | Time-stop dominant |
| SCALP_Aplus_1_Mini_FVG_Retest_NY_Open | 2868 | -0.0445 | 0.376 | **85%** | **Artefact RELAX_CAPS** — conditionnel à B0.1 |
| Morning_Trap_Reversal | 24 | -0.0603 | **1.391** | 0% | Meilleur candidat — énorme MFE non capturé |

### QUARANTINE / PROMOTE candidates (positifs petit échantillon)

| Playbook | Trades | E[R] | avg_peak_R | Commentaire |
|----------|--------|------|------------|-------------|
| IFVG_5m_Sweep | 11 | +0.0330 | 1.011 | +0.363R / 11 tr — besoin plus de data |
| VWAP_Bounce_5m | 3 | +0.0806 | 1.041 | 3 trades — trop peu |
| HTF_Bias_15m_BOS | 3 | +0.0777 | 1.510 | 3 trades — trop peu |

### SILENT (11 playbooks, zéro pattern matches sur 4 semaines)

- **MASTER faithful (6/7) :** FVG_Fill_V065, Liquidity_Raid_V056, Range_FVG_V054, Asia_Sweep_V051, London_Fakeout_V066, OB_Retest_V004
- **Legacy (5) :** London_Sweep_NY_Continuation, Power_Hour_Expansion, BOS_Momentum_Scalp, Trend_Continuation_FVG_Retest, Lunch_Range_Scalp
- **Nouveaux 5m :** EMA_Cross_5m, FVG_Scalp_1m

→ Diagnostic B0.2 obligatoire avant tout fix (taxonomie 2 niveaux : DETECTOR_NEVER_FIRES / SCORING_FILTERS_ALL / RISK_FILTER_KILLS_ALL + sous-catégories SESSION_MISMATCH / HTF_BIAS_GATE / TF_MISMATCH / PATTERN_PRECONDITION_BUG / STRUCTURAL_RARITY).

---

## Enseignements clés

1. **"Famine de cap = seul blocker" est FAUX.** Avec caps bypassés, 11 playbooks restent silents. Le problème est **détecteur**, pas risk filter.
2. **`RISK_EVAL_RELAX_CAPS=true` désactive aussi le cooldown 5 min + cap 10/session/playbook** ([risk_engine.py:379-380](../engines/risk_engine.py)). Les 2868 SCALP_Aplus_1 + 2157 DAY_Aplus_1 sont **partiellement un artefact d'audit** → calibrer dessus produit des valeurs non-production.
3. **NY_Open_Reversal contredit la règle CLAUDE.md "only legacy non-négatif"** — E[R] = -0.21 sur 17 trades fair, WR = 12%. À sortir de l'allowlist opérationnelle.
4. **Variance inter-semaines forte :** DAY_Aplus_1 = -246R (jun) / +8.69R (aug) / -207R (oct) / -67R (nov). Audit 1-semaine insuffisant, 4-semaines nécessaires.
5. **Gate formel échoué (13/28 vs ≥20/28)** mais verdict exploitable : l'enseignement "silent = détecteur, pas cap" est plus précieux que la règle initiale.

---

## Suite (révision roadmap 2026-04-19)

- **A-Close** : commit + CLAUDE.md sync + ce document. **EN COURS.**
- **B0.1** : spam audit SCALP_Aplus_1 + DAY_Aplus_1 (distinguer volume légitime vs artefact RELAX_CAPS).
- **B0.2** : silent playbook funnel diagnosis, taxonomie 2 niveaux.
- **B0.3** : retirer NY_Open_Reversal + ORB_Breakout_5m de AGGRESSIVE_ALLOWLIST.
- **B0.4** : corpus de calibration production-like (allowlist restreinte, caps actives) → input unique de B1.
- **B1** : calibration ciblée sur 4-5 playbooks max (Morning_Trap, Engulfing, BOS_Scalp, Liquidity_Sweep, +SCALP_Aplus_1 conditionnel).
- **B2** : re-audit calibré avec caps normales + split train/test anti-overfit.

Roadmap complète : `/home/dexter/.claude/plans/parsed-nibbling-kettle.md`.
