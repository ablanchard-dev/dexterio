# Phase 5 — SAFE mode : preuve parquet (`labfull_202511`)

**Date :** 2026-04-11  
**Source de vérité trades :** `backend/results/labs/full_playbooks_24m/trades_labfull_202511_AGGRESSIVE_DAILY_SCALP.parquet`  
**Alignement funnel :** `debug_counts_labfull_202511.json` (1634 trades ouverts = 1634 lignes parquet).

---

## PREUVE CODE

Agrégation effectuée avec **pandas** (venv `backend/.venv`) : `r_multiple` par trade, courbe cumulative par playbook, drawdown max sur la série cumulée (min de `cumsum(R) - running_max(cumsum(R))`).

---

## PREUVE RUN

Commande (reproductible depuis `backend/`) :

```bash
.venv/bin/python -c "import pandas as pd; df=pd.read_parquet('results/labs/full_playbooks_24m/trades_labfull_202511_AGGRESSIVE_DAILY_SCALP.parquet'); print(len(df), df['r_multiple'].sum())"
```

Résultat : **1634** lignes, **ΣR ≈ −43.78** (compte tenu des arrondis dans le tableau ci‑dessous).

### Métriques par playbook (chronologique global pour DD intra-playbook)

| Playbook | Trades | Wins | Win rate | ΣR | Avg R / trade | Max DD (courbe cumul R) |
|----------|-------:|-----:|---------:|-----:|--------------:|------------------------:|
| Morning_Trap_Reversal | 369 | 75 | 0.203 | **+1.73** | 0.0047 | **−11.09** |
| Session_Open_Scalp | 39 | 10 | 0.256 | −0.85 | −0.0219 | −1.21 |
| NY_Open_Reversal | 43 | 14 | 0.326 | −1.04 | −0.0241 | −2.15 |
| FVG_Fill_Scalp | 71 | 12 | 0.169 | −4.74 | −0.0667 | −4.55 |
| Trend_Continuation_FVG_Retest | 249 | 22 | 0.088 | −11.78 | −0.0473 | −11.49 |
| Liquidity_Sweep_Scalp | 863 | 202 | 0.234 | −27.11 | −0.0314 | −27.06 |

### `exit_reason` (preuve)

- **NY_Open_Reversal** : SL 24, TP1 9, **session_end** 10 (cohérent Phase 3B fenêtre NY).
- **Liquidity_Sweep_Scalp** : time_stop 765, SL 83, TP1 15.
- **FVG_Fill_Scalp** : time_stop 57, SL 14.
- **Session_Open_Scalp** : time_stop 17, SL 16, TP1 6.
- **Morning_Trap_Reversal** / **TC-FVG** : SL majoritaire + **eod** 15 / 22.

---

## PREUVE TEST

N/A (analyse d’artefact). Les tests **3B** restent dans `tests/test_phase3b_execution.py` (comportement moteur, pas PnL).

---

## ANALYSE

1. **Sur nov 2025 seul**, aucun playbook n’affiche à la fois **expectancy nette forte** et **drawdown faible** : le meilleur **ΣR** est **MTR (+1.73R)** mais avec **WR ~20%** et **DD ~−11R** sur la courbe — peu compatible « sniper elite ».
2. **NY_Open_Reversal** : **−1.04R** sur 43 trades — le pipeline NY **ne doit pas être cassé** pour autant ; ce mois est une **stat d’échantillon**, pas un verdict architecture.
3. **SAFE à 4–5 stratégies** ne peut **pas** être validé uniquement sur ce lab : il faut **autres fenêtres**, **filtres de grade**, ou **rules SAFE** plus strictes (Phase 7).

---

## DÉCISION

| Question | Verdict |
|----------|---------|
| SAFE validé sur `labfull_202511` ? | **NON** (ΣR négatif pour NY, LSS, TC, FVG, Session ; MTR trop rugueux) |
| Données parquet utilisables ? | **KEEP** comme preuve run |
| Suite | **FIX** sélection SAFE = multi-mois + métriques DD / stabilité (hors scope immédiat) |

---

## NEXT STEP — Phase 6

- Élargir **FULL** par **vagues** (allowlist + lab isolé) — voir `PHASE_6_FULL_MODE.md`.
- Pour SAFE : caler un **job multi-fenêtre** (ex. lab rolling) avant de figer `SAFE_ALLOWLIST`.

---

*L’ancien brouillon sans chiffres reste remplacé par ce fichier comme référence Phase 5.*
