# Diagnostic — trades News_Fade `entry_price == stop_loss` (w03 nov2025)

## Contexte

Sur le multi-week nov2025, **9** lignes **News_Fade** dans les parquets présentaient **`entry_price == stop_loss`** avec **`exit_reason == session_end`**, ce qui faisait croire à une géométrie « risque nul » à l’ouverture.

## PREUVE CODE

### Chemin nominal : `Setup` → `Trade` → exécution

1. **`ExecutionEngine.place_order`** crée un `Trade` avec `stop_loss=setup.stop_loss` (niveaux issus du setup / `setup_engine_v2`).

2. **Phase 3B — breakeven** (`update_open_trades`, étape 4) : lorsque `r_multiple >= breakeven_trigger_rr` (News_Fade : **1.0** depuis YAML `breakeven_at_rr: 1.0`), le moteur fait :

```360:371:backend/engines/execution/paper_trading.py
            # 4. Break-even (Phase 3B: seuil par playbook ; legacy: 0.5R)
            if hasattr(trade, 'breakeven_moved'):
                trigger = trade.breakeven_trigger_rr if trade.breakeven_trigger_rr is not None else 0.5
                if not trade.breakeven_moved and r_multiple >= trigger:
                    trade.stop_loss = trade.entry_price
                    trade.breakeven_moved = True
                    events.append({
                        'trade_id': trade_id,
                        'event_type': 'BREAKEVEN_MOVED',
                        'new_sl': trade.entry_price
                    })
```

3. **Clôture** : `close_trade` calcule historiquement `r_multiple` avec `abs(entry - stop_loss)`. Après breakeven, **`stop_loss == entry`** → **risque nul** → **`r_multiple` forcé à 0** (division évitée).

4. **Export** : `_ingest_closed_trades` et la série parquet utilisaient **`trade.stop_loss`** tel quel → **stop final** (breakeven), pas le stop initial.

### Cause exacte (classement des hypothèses)

| Hypothèse | Verdict |
|-----------|---------|
| Journalisation / export | **Oui** — la colonne `stop_loss` exportée reflétait l’état **après** breakeven. |
| Arrondi | **Non** — égalité stricte des flottants côté entrée/stop initial n’explique pas le pattern massif w03. |
| Construction niveaux à l’ouverture | **Non** — à l’ouverture le setup a bien un écart (ex. **0,5 %** via `_calculate_price_levels`). |
| Direction / signe stop | **Non** — SHORT avec stop au-dessus de l’entrée est cohérent. |
| Valeur nulle / fallback | **Non** — c’est la **mutation** du stop vers l’entrée qui annule le dénominateur R. |

## PREUVE RUN

- Relecture des **9** trades w03 : tous **`session_end`**, cohérent avec une tenue après **1R** favorable puis sortie en fin de fenêtre sans retour au stop initial.
- Comportement reproduit en unitaire : `test_news_fade_initial_stop_preserved_after_breakeven_and_r_on_close` (SHORT NF, BE puis `session_end`).

## PREUVE TEST

- `test_news_fade_initial_stop_preserved_after_breakeven_and_r_on_close` — `initial_stop_loss` stable, `r_multiple` non nul à la clôture.
- `test_news_fade_rejects_zero_risk_at_open` — `place_order` refuse **News_Fade** si `entry == stop` au **moment de l’ouverture** (vrai bug de setup, pas BE).

## ANALYSE

Les « trades dégénérés » n’étaient **pas** des ouvertures sans risque : c’était un **artefact de persistance** du stop **après breakeven**. Les audits géométrie / MFE qui utilisaient `stop_loss` parquet **sous-estimaient le risque** et **surestimaient** la dégénérescence.

## DÉCISION

- **Corriger** en conservant **`initial_stop_loss`** à l’ouverture, en utilisant ce niveau pour **R** et pour **`stop_loss` dans `TradeResult` / parquets**, tout en laissant **`stop_loss` mutable** pour les décisions d’exécution (SL / BE).
- **Garde-fou NF** : refus explicite d’ouverture si risque nul au setup.

## Correctif appliqué (chantier 1)

- Modèle `Trade.initial_stop_loss` ; `place_order` remplit et valide NF ; `close_trade` et `update_open_trades` (calcul R) utilisent `initial_stop_loss` si présent ; journal `stop_loss_initial` / `stop_loss_final` ; `TradeResult.stop_loss` = risque initial.

**Chantiers 2–4** (alignement stop YAML, revalidation mini-lab, sweep `tp1_rr`) : **hors périmètre** de ce document — à enchaîner après validation utilisateur.
