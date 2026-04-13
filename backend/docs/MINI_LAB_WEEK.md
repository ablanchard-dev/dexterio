# Mini-lab 1 semaine (post Phase 7 — volatilité / `day_type` dans `market_context`)

## Objectif

Mesurer sur **~7 jours calendaires** le funnel **News_Fade** vs **NY_Open_Reversal**, avec le **même protocole risk** que l’audit D27 / `labfull_202511` :

- `RISK_EVAL_ALLOW_ALL_PLAYBOOKS=false` (allowlists respectées)
- `RISK_EVAL_RELAX_CAPS=true`, `RISK_EVAL_DISABLE_KILL_SWITCH=true`
- `RISK_BYPASS_DYNAMIC_QUARANTINE_LSS_ONLY=true` (bypass quarantaine LSS uniquement)

**Multi-semaines (même protocole, plusieurs labels)** : `scripts/run_mini_lab_multiweek.py --preset nov2025` → funnel consolidé dans `docs/MULTI_WEEK_VALIDATION_NOV2025.md` (source JSON `results/labs/mini_week/consolidated_mini_week_nov2025.json`).

## PREUVE CODE

Runner : `backend/scripts/run_mini_lab_week.py`  
Sorties par label : `backend/results/labs/mini_week/<label>/`

Fichiers générés (après run terminé) :

- `debug_counts_<run_id>.json` — compteurs complets (`matches_by_playbook`, etc.)
- `mini_lab_summary_<label>.json` — extrait **News_Fade** + **NY_Open_Reversal**
- `trades_<run_id>_AGGRESSIVE_DAILY_SCALP.parquet` (si sauvegarde activée par le moteur)
- `trade_journal_<run_id>.parquet` (journal dédié au run)

## PREUVE RUN (commande canonique 1 semaine)

Depuis `backend/` :

```bash
# Une seule instance à la fois (évite verrous / écrasements).
.venv/bin/python scripts/run_mini_lab_week.py \
  --start 2025-11-03 \
  --end 2025-11-09 \
  --label 202511_w01
```

Défauts si args omis : `2025-11-03` → `2025-11-09`, label `202511_w01`, symboles `SPY,QQQ`.

**Smoke plus rapide** (SPY seul, 2 jours) :

```bash
.venv/bin/python scripts/run_mini_lab_week.py \
  --symbols SPY \
  --start 2025-11-03 \
  --end 2025-11-04 \
  --label smoke_spy_2d
```

## Comparaison (run `202511_w01`, **terminé**)

| Référence | Fenêtre | News_Fade M / S / SR / T | NY_Open_Reversal M / S / SR / T |
| --------- | ------- | ------------------------ | -------------------------------- |
| `debug_counts_labfull_202511.json` | 2025-11-01 — 2025-11-30 | **0 / 0 / 0 / 0** | **579 / 436 / 436 / 43** |
| `mini_lab_summary_202511_w01.json` | **2025-11-03 — 2025-11-09** | **110 / 81 / 81 / 9** | **203 / 159 / 159 / 17** |

**Artefacts :** `backend/results/labs/mini_week/202511_w01/` (`mini_lab_summary_202511_w01.json`, `debug_counts_miniweek_202511_w01.json`, trades parquet si écrits par le moteur).

**Preuve run :** `exit_code: 0`, **~964 s** (~16 min), `git_sha` = `a7ab615ae58b743e01b941fe35c5e2766105cfaa`, **425** trades totaux, `final_capital` ≈ **36223.46** (cf. summary JSON).

**Interprétation :** `labfull_202511` a été produit **avant** le câblage Phase 7 (`day_type` / `volatility` → `market_context`) : **News_Fade** restait à **0** match sur le mois. Le mini-lab post–Phase 7 sur la 1ʳᵉ semaine de nov montre **NF** avec funnel non nul et **9** trades ; **NY_Open_Reversal** produit toujours des trades (**17** sur la fenêtre).

### Parquet `trades_miniweek_202511_w01_AGGRESSIVE_DAILY_SCALP.parquet` (aperçu)

| Playbook | Trades | ΣR | `exit_reason` (compte) |
| -------- | -----: | ---: | ---------------------- |
| News_Fade | 9 | ≈ **+0.035** | **session_end** × 9 (Phase 3B fenêtre) |
| NY_Open_Reversal | 17 | ≈ **−1.54** | *(détail : `pd.read_parquet`)* |

## DÉCISION

- **KEEP** le runner mini-lab ; **run `202511_w01` validé** (un seul processus, sorties isolées sous `mini_week/202511_w01/`).

## NEXT STEP

1. **Multi-week nov 2025** : fait — voir `MULTI_WEEK_VALIDATION_NOV2025.md`.
2. **News_Fade / `session_end`** : audit `AUDIT_NEWS_FADE_SESSION_END.md` (preuves CODE / RUN / TEST + options de tweak minimales).
3. **Wave 2** : uniquement après lecture consolidée + audit NF — pas de bascule SAFE/FULL définitive avant nouvelles fenêtres / runs.

