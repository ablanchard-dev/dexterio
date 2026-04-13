# Phases 7 & 8 — Implémentation minimale (2026-04-11)

## Phase 7 — Contexte mesurable (volatilité + wiring)

### Problème (preuve)

`SetupEngineV2.generate_setups` ne passait **ni** `day_type` **ni** `volatility` dans `market_context` → `PlaybookEvaluator._check_basic_filters` voyait `day_type == ''` et `volatility is None` pour les playbooks `news_events_only` / `volatility_min`, ce qui **rejette** News_Fade et Power_Hour (entre autres) **avant** scoring.

### Correctifs (réversibles)

1. **`utils/volatility.py`** : `volatility_score_from_1m(candles, window=30)` — moyenne des true ranges 1m normalisée par le close, × 10 000 (sans lookahead).
2. **`models/market_data.py`** : champ optionnel `volatility: Optional[float] = None` sur `MarketState`.
3. **`backtest/engine.py`** : calcul du score sur `candles_1m` et injection dans `session_info["volatility"]` pour les deux chemins `create_market_state` du hot path + le chemin `multi_tf_candles`.
4. **`engines/market_state.py`** : propagation `volatility` et `current_session` depuis `session_info`.
5. **`engines/setup_engine_v2.py`** : `market_context` inclut `day_type` et `volatility`.

### Preuve test

- `tests/test_volatility_score.py`
- `tests/test_phase2_news_fade_context.py` (réparation tests obsolètes + `test_generate_setups_market_context_contains_day_type_and_volatility`)

### DÉCISION

**KEEP** — améliore la cohérence YAML ↔ runtime ; **NY_Open_Reversal** n’utilise pas `news_events_only`, impact limité sur son filtre temporel.

---

## Phase 8 — Robustesse coûts d’exécution

### Preuve code

`backtest/costs.py` déjà présent (commission IBKR, fees SEC/FINRA vente, slippage %/ticks, spread bps).

### Preuve test

- **`tests/test_backtest_costs.py`** : garde-fous sur `calculate_ibkr_commission`, `calculate_regulatory_fees`, `calculate_slippage`, `calculate_spread_cost`, `calculate_total_execution_costs`.

### DÉCISION

**KEEP** — base pour non-régression ; le branchement **temps réel** des coûts sur chaque close de trade reste un sujet d’audit séparé (`calculate_total_execution_costs` dans le moteur).

---

## NEXT STEP

- Re-lancer un lab court après ce patch pour mesurer l’impact **News_Fade** / **Power_Hour** (matches ↑ attendus si `day_type` + vol OK).
- Vérifier l’alignement **slippage** `settings.SLIPPAGE_TICKS` vs `costs.py` (deux mondes possibles).
