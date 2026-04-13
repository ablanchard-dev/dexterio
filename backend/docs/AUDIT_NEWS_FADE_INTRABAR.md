# Audit — News_Fade : exécution **close-only** vs **intrabar** (1m)

**Objectif :** vérifier si l’absence de TP sur le multi-week **nov2025** (27 trades, 0 TP) peut s’expliquer par une **sous-détection** des TP (moteur sur le **close** uniquement alors que le **high/low** de la minute aurait touché TP1).

**Conclusion anticipée (preuve ci-dessous) :** sur cet échantillon, **aucun** trade n’a vu le prix atteindre **TP1** en **high/low intraminute** pendant la vie du trade. Le goulot principal est donc **le couple objectif 3R + fenêtre / trajectoire de prix**, pas le seul modèle close vs mèche.

**Aucun patch moteur** dans ce livrable — audit uniquement.

---

## PREUVE CODE

### Backtest : un seul prix par symbole et par minute

`_update_positions` construit `market_data[symbol]` avec le **close** de la dernière bougie 1m dont `datetime <= current_time` :

```1933:1945:backend/backtest/engine.py
    def _update_positions(self, current_time: datetime):
        """Met à jour les positions ouvertes avec les prix actuels et ingère les trades fermés."""

        # Récupérer prix actuels à partir des données historiques déjà chargées
        market_data: Dict[str, float] = {}
        for symbol in self.config.symbols:
            symbol_data = self.data[symbol]
            current_bars = symbol_data[symbol_data["datetime"] <= current_time]
            if not current_bars.empty:
                market_data[symbol] = float(current_bars["close"].iloc[-1])

        # Mettre à jour les positions (SL/TP/BE) via ExecutionEngine
        self.execution_engine.update_open_trades(market_data, current_time=current_time)
```

**Valeurs OHLC disponibles dans les données** : les Parquet 1m contiennent `open`, `high`, `low`, `close`, `volume` (index `datetime`). Seul **`close`** est transmis à l’exécution.

### Boucle temporelle : ordre par minute

Pour chaque minute : détection / exécution des setups, puis **mise à jour des positions** :

```905:906:backend/backtest/engine.py
            # 3) Mettre à jour les positions ouvertes
            self._update_positions(current_time)
```

### `ExecutionEngine.update_open_trades` : même scalaire pour SL, session_end, TP

Le prix reçu est noté `current_price` ; **SL**, puis (selon playbook) **session_end** / **TP**, utilisent **exclusivement** ce scalaire — pas de lecture de `high` / `low`.

```215:241:backend/engines/execution/paper_trading.py
            current_price = market_data[trade.symbol]
            
            # Calculer P&L unrealized
            if trade.direction == 'LONG':
                pnl_points = current_price - trade.entry_price
            else:
                pnl_points = trade.entry_price - current_price
            
            # pnl_dollars = pnl_points * trade.position_size  # Unused in update logic
            risk_distance = abs(trade.entry_price - trade.stop_loss)
            r_multiple = pnl_points / risk_distance if risk_distance > 0 else 0
            
            # 1. Vérifier Stop Loss
            if trade.direction == 'LONG' and current_price <= trade.stop_loss:
                trades_to_close.append({
                    'trade_id': trade_id,
                    'reason': 'SL',
                    'close_price': trade.stop_loss
                })
                ...
            elif trade.direction == 'SHORT' and current_price >= trade.stop_loss:
                trades_to_close.append({
                    'trade_id': trade_id,
                    'reason': 'SL',
                    'close_price': trade.stop_loss
                })
                ...
```

Les règles **TP** (via `try_take_profits`) comparent **le même** `current_price` aux niveaux TP1/TP2.

**Synthèse des valeurs utilisées aujourd’hui :**

| Étape backtest | Prix utilisé pour SL / TP / session_end |
|----------------|----------------------------------------|
| Alimentation `market_data` | **Close** 1m (dernière ligne ≤ `current_time`) |
| `update_open_trades` | Ce **close** comme `current_price` unique |
| High / Low intrabar | **Non utilisés** pour les sorties |

### Live / pipeline (hors mini-lab)

`pipeline.update_open_positions` utilise `data_feed.get_latest_price(symbol)` — typiquement un **dernier trade / last**, pas une série OHLC complète dans ce chemin :

```366:375:backend/engines/pipeline.py
        market_data = {}
        for symbol in settings.SYMBOLS:
            price = self.data_feed.get_latest_price(symbol)
            if price:
                market_data[symbol] = price
        
        # Mettre à jour positions
        now = datetime.now(timezone.utc)
        events = self.execution_engine.update_open_trades(market_data, current_time=now)
```

---

## PREUVE RUN

**Données trades :** les 27 lignes **News_Fade** des parquets  
`results/labs/mini_week/202511_w0{1,2,3,4}/trades_miniweek_*_AGGRESSIVE_DAILY_SCALP.parquet`  
(champs `timestamp_entry`, `timestamp_exit`, `symbol`, `direction`, `entry_price`, `stop_loss`, `take_profit_1`, `exit_reason`).

**Données OHLC :** `data/historical/1m/SPY.parquet` et `QQQ.parquet` (même source que `run_mini_lab_week.py` via `historical_data_path`).

**Méthode (reproductible) :** pour chaque trade, fenêtre 1m **`timestamp_entry` ≤ t ≤ `timestamp_exit`** :

- **LONG** : touch TP1 intrabar si `high >= take_profit_1` ; touch SL intrabar si `low <= stop_loss`.
- **SHORT** : touch TP1 intrabar si `low <= take_profit_1` ; touch SL intrabar si `high >= stop_loss`.

**Critère « TP sous-crédité par le close » (fort)** : il existe une bougie où le TP est touché en **high/low**, **pas** le SL sur la même bougie au sens strict (`low > sl` pour LONG, `high < sl` pour SHORT), et pourtant **`close` ne valide pas le TP** (`close < tp1` LONG, `close > tp1` SHORT).

**Résultats numériques (exécution locale audit) :**

| Métrique | Valeur |
|----------|--------:|
| Trades News_Fade | 27 |
| `exit_reason` | `session_end` × 26, `SL` × 1 |
| Au moins une bougie où **`close` aurait dû déclencher TP1** (cohérent moteur actuel) | **0** |
| Au moins une bougie où **intrabar** touche TP1 (high/low) | **0** |
| Cas **forts** « mèche au TP, close non-TP, pas de SL intrabar sur la même bougie » | **0** |
| Bougies **ambiguës** TP+SL même barre | **0** |

**MFE (favorable max) en unités R** pendant la vie du trade (distance entrée → meilleur high pour LONG / meilleur low pour SHORT, divisé par |entrée − stop|) :

- **min / médiane / max** : **0.0 / ~0.10 / ~0.92**
- Trades avec **MFE ≥ 1R** : **0**
- Trades avec **MFE ≥ 3R** (nécessaire pour atteindre TP1 avec `tp1_rr: 3`) : **0**

Interprétation : pendant la fenêtre réellement tenue, le marché **n’a jamais porté le prix jusqu’à TP1**, même en considérant les **mèches 1m**.

---

## PREUVE TEST

- Les tests d’exécution (`tests/test_phase3b_execution.py`, etc.) passent un **prix scalaire** explicite à `update_open_trades` ; **aucun** test n’impose aujourd’hui que le backtest propage **high/low** vers SL/TP.
- Il n’existe pas de test de non-régression « TP intrabar OHLC » pour le moteur — ce n’est pas un échec de CI, c’est un **trou de spécification** documenté ici.

---

## ANALYSE

1. **Modèle actuel** : le backtest est **volontairement ou de fait** un modèle **« un prix par minute »** = **close** de la minute pour toutes les sorties. Les **high/low** ne participent pas aux décisions SL/TP/session_end.

2. **Échantillon nov2025** : même en élargissant la question aux **mèches 1m**, **0 / 27** trades auraient pu être crédités **TP1** sans changer la cible 3R. La limite est **structurelle** : **MFE max ~0.92R** alors que **TP1 exige ~3R**.

3. Le patch précédent « **TP avant session_end** (NF-only) » ne peut rien corriger si **le prix n’atteint jamais TP1** avant la fin de fenêtre — ce que confirme l’audit OHLC.

4. **Risque théorique non observé ici** : sur d’autres périodes, on pourrait avoir **`high` ≥ TP1** et **`close` < TP1** sur une même minute ; le moteur actuel **ne créditerait pas** le TP. Ce scénario **n’apparaît pas** sur les 27 trades NF nov2025.

---

## DÉCISION

- **Ne pas prioriser** un patch **NF-only intrabar** sur la base du multi-week **nov2025** : **impact attendu = 0 trade** sur cet échantillon (estimation : **0** trade basculerait vers TP1).
- Le **vrai levier** pour voir des TP sur ce playbook, sur ces données, est plutôt **métier / YAML** (ex. **abaisser `tp1_rr`**, élargir la fenêtre de détention si cohérent avec la thèse du fade, ou revoir la définition du stop) — **à traiter dans un ticket séparé**, pas comme « fix intrabar ».

---

## NEXT STEP

1. Si tu veux **valider d’autres mois** : réutiliser la même méthode sur d’autres parquets mini-week / labfull (script ad hoc ou notebook) avant tout patch intrabar.
2. Si un patch intrabar est un jour justifié : le concevoir **NF-only**, avec règle explicite **TP vs SL** sur la même bougie (open-first, pessimiste SL-first, etc.) — **hors périmètre** tant qu’aucun échantillon ne montre de cas « mèche TP / close non-TP ».
3. Mettre à jour la doc produit / playbook si la décision est de **garder 3R** : accepter que beaucoup de sorties restent **`session_end`** ou **SL** sans TP sur des fenêtres courtes.
