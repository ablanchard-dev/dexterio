# Dossier — Leg 4.2 VIX-regime overlay sur cohort survivor_v1 (§18 adapted overlay)

**Statut** : OVERLAY_SPECIFIED
**Date** : 2026-04-22
**Leg** : 4.2 (plan §0.5 arbre)
**Type** : filtre régime post-hoc read-only (PAS un nouveau playbook)

---

## Pièce A — identité

- **Nom canonique** : Leg42_VIX_Regime_Overlay_v1
- **Version** : v1
- **Famille** : régime filter (overlay) — catégorie plan §0.7
- **Type** : read-only cross-playbook régime gate
- **Cohort cible** : `survivor_v1` restreint aux 4 survivors (News_Fade + Engulfing_Bar_V056 + Session_Open_Scalp + Liquidity_Sweep_Scalp) cf [survivor_v1_verdict.md](backend/data/backtest_results/survivor_v1_verdict.md)
- **Instruments** : SPY, QQQ (hérités cohort)
- **Timeframes** : trades pré-existants (1m/5m) + daily VIX pour gate
- **Source VIX** : yfinance `^VIX` daily close (fetched ad-hoc, pas ingesté localement — cf §0.7 tech debt)

## Pièce B — hypothèse formelle

- **Thèse** : la cohort 4-survivors `survivor_v1` à E[R] proche de zéro (-0.009 à -0.022 selon k-pack) contient une proportion de trades pris en régime **vol-low** ou **vol-panic** (§0.4-bis). Restreindre la cohort au subset **VIX_close prior-day ∈ [15, 25]** (régime fertile mean-rev) doit soit révéler un edge positif soit confirmer que le régime n'est pas le bottleneck.
- **Mécanisme** : la littérature quant (cf plan §5.3 P4) associe mean-rev SPY/QQQ à vol fertile (VIX 15-25) ; low-vol = trending/microstructure, high-vol = directional/panic. Les 4 survivors sont mean-rev / reversal par nature.
- **Conditions de fertilité** : prior-day VIX_close ∈ [15, 25].
- **Conditions de stérilité** : VIX < 15 (low-vol trending dominant) OR VIX ≥ 25 (panic / trend breakout).
- **Risque principal / falsifiabilité** : corpus jun-nov 2025 est **déjà ~89% dans la bande [15,25]** (mesure empirique VIX via yfinance). Si subset retire seulement ~11% des trades, l'effet attendu sera minime ; c'est un fort indicateur que VIX-regime n'est pas le filtre discriminant.

## Pièce C — spécification d'état décisionnel

- **Gate** : pour chaque trade `t` dans cohort, calculer `VIX_close_prior_day(t)` (close daily VIX du dernier jour de trading strictement avant `trading_date(t)`).
- **Accept** : `VIX_close_prior_day ∈ [15, 25]`
- **Reject** : sinon
- **Agrégation** : recompute E[R], WR, PF, n sur subset accepted par playbook et cohort globale.
- **Pas de logique séquentielle** — filtre stateless par trade.

## Pièce D — dépendances + audit infra

- **Requis** :
  - Daily VIX series jun-nov 2025 (yfinance)
  - Trades parquet `survivor_v1` (déjà disponible : 4 semaines × 4 survivors)
  - Pandas merge `asof` par trading_date
- **Audit** : `full infra exists` — rien à construire côté moteur (overlay read-only).

## Pièce E — configuration

```python
SURVIVOR_PLAYBOOKS = ["News_Fade", "Engulfing_Bar_V056", "Session_Open_Scalp", "Liquidity_Sweep_Scalp"]
VIX_BAND_LOW = 15.0
VIX_BAND_HIGH = 25.0
CORPUS_WEEKS = ["jun_w3", "aug_w3", "oct_w2", "nov_w4"]
```

Harness : [backend/scripts/leg42_vix_overlay.py](backend/scripts/leg42_vix_overlay.py) (à créer, ~100 lignes).

## Pièce F — tests

Pas de tests unitaires — overlay read-only 100 lignes, logique évidente (merge_asof + .between(15,25)). §19.3 budget — réutilise briques Pandas testées en amont.

## Pièce G — protocole

1. Charger 4 trades parquets `survivor_v1/{week}/trades_...parquet`
2. Filtrer subset cohort = 4 survivors
3. Fetch VIX daily via yfinance (2025-05-01 → 2025-11-30 pour buffer prior-day)
4. Merge_asof trading_date ↔ VIX close (prior-day strict)
5. Compute baseline cohort : n, E[R], WR, PF
6. Compute subset VIX ∈ [15,25] : n, E[R], WR, PF, Δ
7. Per-playbook split : idem
8. Autres régimes bandes §0.4-bis : VIX<15 (low), VIX≥25 (panic) — calculer aussi
9. Verdict §18.3

## Pièce H — kill rules pré-écrites

1. **Subset cohort E[R] gross ≤ 0.05R** → FAIL → Leg 5 ESCALADE USER
2. **n subset < 30** → INCONCLUSIVE (corpus insuffisant) → escalade data Polygon ingestion
3. **E[R] subset < E[R] baseline cohort** → FAIL hard (régime filter destructeur)

Si subset E[R] > 0.05R **ET** n ≥ 30 → PASS partiel → considérer corpus expansion pour confirmer Stage 1 gate (§0.6).
