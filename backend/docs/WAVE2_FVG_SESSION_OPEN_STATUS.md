# Wave 2 — Statut FVG_Fill_Scalp & Session_Open_Scalp (repo-driven)

## A. Diagnostic (preuves chiffrées)

### Source A — `mini_lab_summary_202511_w01.json` (baseline `mini_week/202511_w01/`)

| Playbook | matches | setups | after_risk | trades |
|----------|--------:|-------:|-----------:|-------:|
| FVG_Fill_Scalp | 67 | 67 | 67 | 17 |
| Session_Open_Scalp | 15 | 9 | 9 | 9 |

### Source B — `mini_lab_summary_202509_w01.json` (`nf1r_confirm_sep2025/202509_w01/`, YAML canonique NF 1.0R)

| Playbook | matches | setups | after_risk | trades |
|----------|--------:|-------:|-----------:|-------:|
| FVG_Fill_Scalp | 0 | 0 | 0 | 0 |
| Session_Open_Scalp | 18 | 12 | 12 | 12 |

### Lecture

- **Session_Open_Scalp** : funnel **non nul** sur les deux fenêtres ; trades exécutés.
- **FVG_Fill_Scalp** : **forte dépendance au régime / semaine** — actif sur nov w01, **aucun match** sur sep w01 (même runner, même allowlist AGGRESSIVE).
- Alignement avec `docs/WAVE2_PLAN_FVG_SESSIONOPEN_NEWSFADE.md` : goulot FVG côté **setup / patterns ICT** (FVG présents sur 1m), pas uniquement risk.

## B. Décision technique (goulot principal)

| Playbook | Goulot principal |
|----------|------------------|
| FVG_Fill_Scalp | **Funnel setup amont** (matches ICT FVG + filtres jour/trend) |
| Session_Open_Scalp | **READY_WITH_LIMITATIONS** — funnel OK ; volumes modérés |

## C. Patch minimal (cette livraison)

**Aucun patch moteur** — diagnostic seulement. Tout changement FVG (détection 1m, filtre trend, RR edge) exige mini-lab ciblé + preuve non-régression NY.

## D. Tests & mini-lab

- Tests existants playbooks / risk non modifiés ici.
- Mini-lab ciblé futur : 1 semaine + assert `matches_by_playbook["FVG_Fill_Scalp"] > 0` après patch documenté dans WAVE2 plan.

## E. Verdict

| Playbook | Verdict |
|----------|---------|
| FVG_Fill_Scalp | **NEEDS_SECOND_PATCH** (hors scope de ce commit ; preuve sep w01 = 0 match) |
| Session_Open_Scalp | **READY_WITH_LIMITATIONS** (trades > 0 ; surveiller sur plus de fenêtres) |

## NEXT (Wave 2)

1. Instrumenter `setup_engine_reject_reasons` / FVG sur run court **FVG-only** (symbole unique) selon plan Wave 2.
2. Un seul levier à la fois (YAML filtre **ou** scope détection **uniquement** `FVG_Fill_Scalp`).
