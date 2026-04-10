# Phase 3B — exécution Wave 1 et **comparabilité historique**

## Ce que 3B change (volontairement, pas un « micro-fix »)

La Phase 3B modifie la **sémantique d’exécution** pour trois playbooks uniquement (`NY_Open_Reversal`, `News_Fade`, `Liquidity_Sweep_Scalp`), derrière la garde `PHASE_3B_PLAYBOOKS`. Ce n’est **pas** une correction invisible : toute série de résultats obtenue **avant** cette sémantique **n’est pas directement comparable** aux runs **après**, pour les métriques qui dépendent des sorties et du chemin de prix intratrade.

En particulier pour **NY_Open_Reversal** et **News_Fade** (DAILY) :

- **`session_end`** : clôture à la borne de fin de fenêtre dérivée du YAML (timezone `America/New_York`), au lieu de prolonger jusqu’à une sortie **EOD** implicite pour une partie des trades.
- **Breakeven à `breakeven_at_rr` du YAML (1.0R)** au lieu du seuil global historique **0.5R** (qui, de plus, ne s’appliquait pas correctement tant que `Trade.breakeven_moved` n’existait pas sur le modèle).

Pour **Liquidity_Sweep_Scalp** :

- **Time-stop à `max_duration_minutes` (30)** issu du YAML, au lieu du plafond global `_max_scalp_minutes` (souvent 120).

Conséquences sur les indicateurs agrégés : **distribution des R**, nombre et type de **wins/losses/breakevens**, **profit factor**, **exit_reason** (apparition de `session_end`, redistribution entre `eod` / `time_stop` / SL après BE), et donc **courbes d’équité** et comparaisons « lab Nov 2025 vs lab Nov 2025 » si l’un des deux n’est pas sur la même version d’exécution.

**À ne pas faire :** présenter 3B comme un changement neutre pour l’historique NY/NF ou comme une simple « fidélité YAML » sans impact sur les séries temporelles — l’impact est **structurel** sur le lifecycle du trade.

---

## Baseline « pré-3B » (référence chiffrée, même fenêtre lab)

Référence : fenêtre **`labfull_202511`** (SPY+QQQ, `summary_labfull_202511_AGGRESSIVE_DAILY_SCALP.json` + `trades_labfull_202511_AGGRESSIVE_DAILY_SCALP.parquet`) tels que présents sur disque **avant** régénération post-3B.

Résumé agrégé (summary) :

| Indicateur | Valeur |
|------------|--------:|
| `total_trades` | 170 |
| `total_pnl_r` | ≈ 11.53 |
| `NY_Open_Reversal` trades | 162 |
| `NY_Open_Reversal` `total_r` | ≈ 15.80 |
| `Liquidity_Sweep_Scalp` trades | 8 |
| `Liquidity_Sweep_Scalp` `total_r` | ≈ −4.27 |
| `News_Fade` | 0 trade dans ce export parquet (fenêtre / concurrence) |

Répartition des **exit_reason** (parquet, même run) :

| Playbook | exit_reason | count |
|----------|-------------|------:|
| NY_Open_Reversal | SL | 66 |
| NY_Open_Reversal | TP1 | 58 |
| NY_Open_Reversal | eod | 38 |
| Liquidity_Sweep_Scalp | SL | 2 |
| Liquidity_Sweep_Scalp | TP1 | 1 |
| Liquidity_Sweep_Scalp | time_stop | 5 |

Interprétation baseline : une part significative des NY se termine encore en **`eod`** ; après 3B, on attend une **baisse** de `eod` au profit de **`session_end`** (et des sorties modifiées après BE 1R).

---

## Run de validation post-3B (même protocole que le lab court P2)

```powershell
Set-Location c:\bots\dexterio1-main
python backend/scripts/run_full_playbooks_lab.py `
  --months 1 --anchor-end 2025-11-28 --symbols SPY,QQQ `
  --respect-allowlists --risk-bypass-dynamic-quarantine-lss-only
```

Après exécution :

1. Lire `backend/results/labs/full_playbooks_24m/summary_labfull_202511_AGGRESSIVE_DAILY_SCALP.json` (`stats_by_playbook`, `total_trades`, `total_pnl_r`).
2. Agréger les sorties sur le parquet trades :

```powershell
Set-Location c:\bots\dexterio1-main\backend
python -c "import pandas as pd; df=pd.read_parquet('results/labs/full_playbooks_24m/trades_labfull_202511_AGGRESSIVE_DAILY_SCALP.parquet'); print(df.groupby(['playbook','exit_reason']).size())"
```

3. Comparer **avant/après** pour NY / NF / LSS : trades, `total_r`, tableau `exit_reason`, et présence de **`session_end`** sur NY/NF.
4. **News_Fade — concurrence post-risk (sélection `max(final_score)`) :** dans `debug_counts_labfull_*.json`, lire `news_fade_post_risk_final_pool_count`, `news_fade_post_risk_lost_final_selection_count`, `news_fade_post_risk_lost_final_selection_by_winner` et `news_fade_post_risk_won_final_selection_count`. La part de NF présente dans le pool final mais écartée au profit d’un autre playbook vaut `lost_final_selection_count / final_pool_count` (si `final_pool_count > 0`).

**Sauvegarde recommandée :** avant de régénérer, copier les fichiers `summary_*`, `trades_*.parquet` / `.csv` et `debug_counts_*` sous un suffixe `_pre_phase3b_execution` pour garder une preuve reproductible côte à côte.

---

## Critères de succès / échec de la validation

- **Succès** : les sorties reflètent la policy (ex. `session_end` sur NY/NF lorsque la session dépasse la fenêtre ; LSS `time_stop` cohérent avec 30 min ; BE observable seulement après 1R pour NY/NF dans les cas testés). Les totaux **peuvent** diverger fortement du baseline — ce n’est pas un échec en soi.
- **Échec / rollback** : régression sur playbooks **hors** `PHASE3B_PLAYBOOKS` ; absence totale de `session_end` alors que des `eod` NY subsistent uniquement par bug TZ ; LSS sans `max_hold_minutes` sur le trade.

---

## Phase 4 — enchaînement (audit D27)

Après **re-baseline** des métriques Wave 1 sur la sémantique 3B (au moins un lab court + export `exit_reason` archivé), la suite logique est l’**audit / gate Phase 4** (référence interne **D27** : définition opérationnelle à figer dans le backlog d’audit — délai, périmètre symboles, et critères d’acceptation par playbook une fois les séries comparables).

---

## Références code

- Garde et fenêtres : `backend/engines/execution/phase3b_execution.py`
- Paper : `backend/engines/execution/paper_trading.py`
- Parité backtest SCALP : `backend/backtest/engine.py` (`_effective_max_scalp_minutes_for_trade`)
- Tests : `backend/tests/test_phase3b_execution.py`
