# Phase 3 — Validation 3B (exécution réaliste) (PREUVE)

**Date :** 2026-04-11  
**Périmètre Wave 1 :** `NY_Open_Reversal`, `News_Fade`, `Liquidity_Sweep_Scalp` (`PHASE3B_PLAYBOOKS`).

---

## PREUVE CODE

### Modèle `Trade`

Champs déjà présents : `breakeven_trigger_rr`, `max_hold_minutes`, `session_window_end_utc`, `breakeven_moved`.

```100:104:/home/dexter/dexterio1-main/backend/models/trade.py
    # Phase 3B: paramètres d'exécution spécifiques par playbook (optionnels)
    breakeven_trigger_rr: Optional[float] = None
    breakeven_moved: bool = False
    session_window_end_utc: Optional[datetime] = None
    max_hold_minutes: Optional[float] = None
```

### Placement d’ordre (`paper_trading.py`)

- **DAILY** + Phase3B : `breakeven_trigger_rr` depuis `pb_def.breakeven_at_rr` (fallback 1.0) ; `session_window_end_utc` via `compute_session_window_end_utc` pour NY / News_Fade uniquement (`should_attach_session_window_end`).
- **SCALP** + Phase3B : `max_hold_minutes` depuis `pb_def.max_duration_minutes` (ex. LSS **30** dans YAML).

### Mise à jour positions

- **Session end** : clôture si `current_time >= session_window_end_utc` (DAILY).
- **Time stop SCALP** : `max_hold_minutes` si défini, sinon cap global `_max_scalp_minutes`.
- **Breakeven** : seuil = `breakeven_trigger_rr` si défini, sinon **0.5R** (legacy).

### YAML (extraits)

- `NY_Open_Reversal` : `time_range: ["09:30", "11:00"]`, `breakeven_at_rr: 1.0`.
- `News_Fade` : `time_windows` incl. `["09:30", "11:00"]` et `["14:00", "15:30"]`, `breakeven_at_rr: 1.0`.
- `Liquidity_Sweep_Scalp` : `max_duration_minutes: 30` (dans la section SCALP du YAML).

---

## PREUVE RUN

```text
cd backend && .venv/bin/python -m pytest tests/test_phase3b_execution.py -q
```

**Résultat :** **8 passed** (venv local `backend/.venv`, deps `requirements.txt`).

Tests couvrant notamment :

- Breakeven **1R** NY / News_Fade (pas 0.5R).
- Time stop LSS **30 min** avec cap global 120.
- Session end News_Fade après `session_window_end_utc`.
- Legacy : breakeven **0.5R** si `breakeven_trigger_rr is None` ; time stop global pour scalps sans `max_hold_minutes`.

---

## PREUVE TEST

- Fichier : `backend/tests/test_phase3b_execution.py`.
- **8** tests, **0** échec (run du 2026-04-11).

---

## ANALYSE

- Les exigences Phase 3 listées dans le cahier (breakeven NY/NF 1R, LSS 0.5R implicite via legacy quand pas de trigger dédié pour scalps — **LSS** reçoit `max_hold` playbook, pas `breakeven_trigger_rr`, donc breakeven reste **0.5R** tant que non surchargé) sont **alignées** avec le code et les tests.
- **LSS** : time stop **30 min** playbook est **prouvé** par test ; breakeven **0.5R** est le chemin legacy (cohérent avec `test_legacy_playbook` pattern pour autres scalps).

---

## DÉCISION

| Sujet | Verdict |
|--------|---------|
| Implémentation 3B Wave 1 | **KEEP** |
| Tests | **KEEP** (suite verte dans venv) |
| Extension à d’autres playbooks | **Hors Phase 3 close** — élargir `PHASE3B_PLAYBOOKS` seulement avec tests dédiés |

---

## NEXT STEP

- Phase 4 : funnel M/S/SR/T par playbook (s’appuyer sur `debug_counts_*.json` + `D27_PORTFOLIO_AUDIT_labfull_202511.md`).
- Si tu veux **LSS breakeven explicite 0.5R** dans le modèle : setter `breakeven_trigger_rr=0.5` dans `place_order` pour LSS (patch **minimal** + test).
