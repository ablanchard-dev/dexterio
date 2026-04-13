# Ré-audit géométrie **News_Fade** — nov2025 **après** `initial_stop_loss`

**Contexte :** suite au correctif d’export (`Trade.initial_stop_loss` → `TradeResult.stop_loss` / parquets), refaire la géométrie sur **les mêmes fenêtres** sans exclure artificiellement les trades w03. **Aucun changement YAML ni moteur supplémentaire** dans cette passe.

**Référence diagnostic :** `DIAGNOSTIC_NF_W03_ENTRY_EQ_STOP.md`

---

## PREUVE CODE

- Les parquets mini-lab (`trades_miniweek_<label>_AGGRESSIVE_DAILY_SCALP.parquet`) sont alimentés depuis `TradeResult`, où **`stop_loss`** est désormais le **stop initial** si présent :

```2345:2351:backend/backtest/engine.py
                stop_loss=(
                    trade.initial_stop_loss
                    if getattr(trade, "initial_stop_loss", None) is not None
                    else trade.stop_loss
                ),
```

- Méthode d’audit (inchangée) : pour chaque ligne **News_Fade**, `risk_pts = |entry − stop_loss|` (parquet), MFE/MAE en **R** sur bougies 1m **\[timestamp_entry, timestamp_exit\]**, OHLC `data/historical/1m/{SPY,QQQ}.parquet`.

---

## PREUVE RUN

**Commande :** depuis `backend/` —  
` .venv/bin/python scripts/run_mini_lab_multiweek.py --preset nov2025`  
→ **`exit_code: 0`**, durée ~**62 min** (session agent), agrégation écrite :

- `results/labs/mini_week/consolidated_mini_week_nov2025.json`
- `docs/MULTI_WEEK_VALIDATION_NOV2025.md`

**Artefacts trades :**  
`results/labs/mini_week/202511_w0{1,2,3,4}/trades_miniweek_*_AGGRESSIVE_DAILY_SCALP.parquet` (régénérés).

**Échantillon News_Fade :** **27** trades (identique au funnel précédent).

| Contrôle post-fix | Valeur |
|-------------------|--------:|
| Trades avec `risk_pts ≈ 0` (dégénéré) | **0** / 27 |
| `exit_reason` | `session_end` × 26, `SL` × 1 |

### Grille **MFE** (nombre de trades ayant atteint ≥ seuil au moins une fois, **n = 27**)

| Seuil | Count / 27 |
|-------|------------|
| ≥ 0,25 R | 19 |
| ≥ 0,50 R | 16 |
| ≥ 0,75 R | 14 |
| ≥ **1,0 R** | **9** |
| ≥ 1,5 R | 3 |
| ≥ 2,0 R | **0** |
| ≥ **3,0 R** (TP1 à 3R) | **0** |

### Grille **MAE** (n = 27)

| Seuil | Count / 27 |
|-------|------------|
| ≥ 0,25 R | 11 |
| ≥ 0,50 R | 3 |
| ≥ 0,75 R | 2 |
| ≥ 1,0 R | 1 |

### **MFE_R** (valide, n = 27)

- min / 25% / **médiane** / 75% / **max** : **0,027 / 0,20 / 0,77 / 1,23 / 1,73**
- Moyenne : **~0,73 R**

**RR géométrique** `|TP1 − entry| / risk` : **3,0** sur tous les trades (inchangé, cohérent `tp1_rr: 3`).

---

## PREUVE TEST

- Régression chantier 1 :  
  `pytest tests/test_phase3b_execution.py -q` → **12 passed** (même module qu’après `initial_stop_loss`).

---

## ANALYSE

1. **Correction représentation :** plus aucun trade NF n’apparaît avec `entry == stop` dans les parquets ; les **9** cas w03 sont bien **réintégrés** avec un **risque initial ~3 pts** (ordre de grandeur inchangé vs avant bug d’export).

2. **Nouvelle lecture MFE :** **9 / 27** trades atteignent au moins **1R** favorable intraminute pendant la vie du trade (vs **0 / 18** « valides » avant correctif, où le dénominateur R était cassé sur w03). La trajectoire de prix **peut** donc dépasser **1R** ; elle **ne dépasse jamais 2R** ni **3R** sur cet échantillon (**max MFE ≈ 1,73 R**).

3. **Conclusion « 3R trop loin » :** elle **reste vraie** : **0 / 27** n’atteignent **3R** de MFE, donc **TP1 (3R)** reste **hors d’atteinte** en excursion 1m sur nov2025, **même après** export correct des stops initiaux.

4. **Nuance :** on peut désormais argumenter qu’un objectif **entre 1R et ~1,7R** toucherait une **part non nulle** des trades (selon seuil choisi), alors que **3R** reste au-dessus du **max observé**.

---

## DÉCISION

- **Révalidation OK** : parquets cohérents avec **`initial_stop_loss`**, grille MFE/MAE recalculée sur **27** trades sans exclusion artificielle w03.
- **Feu vert conceptuel** pour enchaîner le **chantier suivant** (alignement stop NF **ou** sweep `tp1_rr`), **sans** remettre en cause le diagnostic « **TP à 3R trop ambitieux** pour ce dataset ».

---

## NEXT STEP

1. **Chantier 2** (ta roadmap) : décision **YAML vs moteur** pour le stop NF (`0,5 %` documenté **ou** `spike_extreme` + padding), patch **minimal** et **NF-centric** si tu le valides.
2. **Chantier 4** (si tu repousses le stop) : sweep **`tp1_rr`** borné (1,0 / 1,25 / 1,5 / 2,0) avec les **mêmes** métriques (ΣR, winrate, `exit_reason`, MFE vs cible).

---

*Script de reproduction : même bloc Python que pour `AUDIT_NEWS_FADE_GEOMETRY.md`, appliqué aux parquets régénérés après le run `nov2025` ci-dessus.*
