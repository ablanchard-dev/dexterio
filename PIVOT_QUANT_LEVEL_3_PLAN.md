# Dexterio — Pivot vers Niveau 3 quant retail-adapté

**Date** : 2026-05-25
**Statut** : PLAN CONDITIONNEL — pas encore lancé
**Décision opérateur** : on lance Dexterio quant **uniquement si** HyperDex
copy-trading ne maximise pas son edge attendu ou si les quant gates ajoutés sur
HyperDex ne produisent pas une amélioration spectaculaire.

---

## 1. POURQUOI CE DOC

Dexterio est en pause de facto depuis avril 2026. Dernier verdict
(`fe01804 — plan v4.0 week complete`) = **16 data points negative convergent**,
aucune stratégie ICT/SMC testée n'a démontré un edge robuste OOS sur corpus
étendu 2019-2025.

Plutôt que d'abandonner totalement, on documente ici le **plan de pivot**
vers une vraie stratégie quant Niveau 3 retail-adaptée, à activer comme
**option backup** si le projet HyperDex (copy-trading Hyperliquid) plateau.

## 2. POURQUOI NIVEAU 3 ET PAS NIVEAU 2.5

**Niveau 3 pur** (Renaissance / Citadel / Two Sigma) demande 50-200 PhDs +
infrastructure co-localisée + données alternatives à $10M+/an. Impossible solo.

**Niveau 3 retail-adapté** que ce projet vise :
- ML ensemble (LightGBM + neural nets + RL pour execution)
- Walk-forward + purged k-fold + Bayesian backtest overfitting probability
  + multi-testing correction (Bonferroni / FDR)
- Monte Carlo stress tests + VaR/CVaR + tail risk explicite
- Optimal execution (Almgren-Chriss + dynamic slippage)
- Microstructure-aware (orderbook depth, queue position, VPIN toxicity)
- Production-grade : low-latency Python + Rust hot-path, fault tolerant,
  monitoring 24/7
- Multi-strategy portfolio (factor + stat arb + vol selling)
- Auto-retraining pipeline (modèle refresh hebdomadaire)
- Causal inference pour feature selection (vs juste corrélation)

**EXPLICITEMENT exclu** (hors portée solo retail) :
- HFT sub-microseconde (co-location $20k+/mois)
- Données alt premium (satellite, credit card)
- Options exotiques calcul stochastique pur (niche industrielle)
- Equity stat arb US large cap (Renaissance domine)

## 3. ASSET CLASS CIBLE : CRYPTO PERP

Choix stratégique :
- Moins compétitif que equity US
- Données accessibles gratuitement (Hyperliquid, Binance, Bybit APIs)
- Microstructure intéressante (24/7, funding rates, basis)
- Infrastructure réutilisable depuis HyperDex
- Niches identifiables : intraday alpha 5m-1h, alt funding arb,
  mid-cap mean reversion

## 4. ARCHITECTURE — CE QU'ON GARDE DE DEXTERIO

**Récupérable à 60%** (asset stratégique n°1) :

| Composant | Statut | Rôle dans pivot quant |
|---|---|---|
| `backtest/engine.py` Phase 2.3 optimisé | ✅ Garder | Bar-by-bar replay, incremental aggregation, caching |
| `backtest/costs.py` (IBKR + SEC/FINRA + slippage + spread) | ✅ Garder | Modèle frais réaliste |
| `backtest/metrics.py` (Sharpe, expectancy, MDD, PF) | ✅ Garder | Métriques standards |
| `engines/stat_arb/` (cointegration, zscore, sizing, tracker) | ✅ Garder + étendre | Foundation stat arb crypto pairs |
| `engines/regime/classifier.py` | ✅ Garder + étendre | Régime detection multi-asset |
| `engines/features/` (11 features) | ✅ Garder, étendre à 100+ | Features structurelles |
| `research/feature_store.py` | ✅ Garder | Pipeline features |
| `research/label_factory.py` | ✅ Garder + étendre triple-barrier | Labels ML |
| `research/quality_report.py` | ✅ Garder | Data quality checks |
| `risk_engine.py` | ✅ Garder + étendre VaR/CVaR | Risk control |
| `execution/paper_trading.py` + `fill_model.py` | ✅ Garder | Paper layer |
| `engines/patterns/` (ICT/SMC/IFVG/BOS) | ❌ Archiver | Pivot remplace cette couche |
| `engines/setup_engine*.py` | ❌ Archiver | Pivot remplace |
| `engines/aplus01_driver.py`, `smt_driver.py` | ❌ Archiver | Pivot remplace |

**À ajouter de zéro** :
- ML pipeline (LightGBM + PyTorch + walk-forward purged CV)
- Bayesian backtest overfitting probability
- Monte Carlo risk simulator
- Almgren-Chriss execution
- Multi-exchange data ingestion (ClickHouse)
- Rust hot-path execution layer
- MLflow tracking + DVC data versioning
- Grafana monitoring stack

## 5. PLAN 8 PHASES (18-24 MOIS)

### Phase 0 — Setup infra (2 sem)
- Repo `dexterio v2` fork du repo actuel, branch `quant-v1`
- Setup cloud Hetzner/OVH (~€100/mois)
- Docker compose : ClickHouse + Postgres + Redis + Grafana + Prometheus
- Secrets vault (1Password / HashiCorp Vault gratuit)
- CI/CD basique (GitHub Actions tests)
- **Gate** : smoke test E2E ingestion → query → backtest

### Phase 1 — Data pipeline 24/7 (4 sem)
- Ingestion temps réel : OHLCV 1s/1m + L2 orderbook + funding + open interest
- Sources : Hyperliquid (déjà), Binance, Bybit
- Backfill 5 ans historiques
- Quality monitoring : gap detection, anomaly detection
- **Gate** : coverage >99%, gaps <0.1%, latency <500ms

### Phase 2 — Feature engineering (6-8 sem)
- 100+ features catégorisées :
  - **Momentum** : returns multi-horizon, cross-sectional rank
  - **Mean reversion** : z-score, RSI, distance VWAP
  - **Volatility** : realized vol, vol-of-vol, vol ratio
  - **Microstructure** : orderbook imbalance, BBO spread, VPIN
  - **Cross-asset** : BTC dominance, alt-major correlation, sector beta
  - **Funding/basis** : funding spread, basis term structure
  - **Sentiment** : aggregated liquidations, fear/greed proxies
- Feature store enrichi + tests stationnarité
- **Gate** : feature stability >0.7 (rolling 30d), no leakage proof

### Phase 3 — Label factory (2-3 sem)
- Triple-barrier method (López de Prado) : take-profit, stop-loss, time-out
- Meta-labeling : modèle 1 direction, modèle 2 confiance
- Horizons multiples : 5m, 15m, 1h, 4h
- **Gate** : label balance check, no leakage cross-validation

### Phase 4 — ML R&D (12-16 sem) — LE GROS MORCEAU
- Modèles testés progressivement :
  1. Ridge/Lasso baseline
  2. LightGBM / XGBoost (sweet spot retail)
  3. Random Forest (variance check)
  4. Neural nets (MLP simple → TabTransformer si data >>)
  5. RL execution (PPO sur Almgren-Chriss)
- Validation rigoureuse :
  - Walk-forward purged k-fold
  - Bootstrap pour confiance intervalles
  - Bayesian backtest overfitting probability (Bailey-López de Prado)
  - Bonferroni / FDR-BH si N modèles testés
- Tracking : MLflow + DVC
- **Gate** : OOS Sharpe ≥1.2, PBO <0.1, t-stat>3 sur holdout fresh

### Phase 5 — Portfolio + risk (4-6 sem)
- Position sizing : Kelly fractionnel + vol targeting
- Portfolio optimization : Markowitz mean-variance (Riskfolio-Lib)
- Risk parity : équilibrer contributions risque
- Stress tests : Monte Carlo (vol spike, correlation breakdown, flash crash)
- VaR/CVaR + tail risk explicite
- Kill-switch + circuit breakers
- **Gate** : stress tests passent, DD<15% backtest worst-case

### Phase 6 — Execution optimisée (4-6 sem)
- Almgren-Chriss optimal execution schedule
- Dynamic slippage model basé orderbook + recent vol
- Smart order routing (limit re-quote, IOC, post-only maker)
- Rust hot-path pour orders critiques (latence)
- **Gate** : slippage modeled vs realized <30% différence

### Phase 7 — Paper trading (12 sem)
- Bot 24/7 paper sur toutes les stratégies validées
- Monitoring strict : Sharpe rolling, DD, hit rate, fee/slippage drag
- A/B testing variants shadow mode
- Alpha decay tracking
- **Gate** : Sharpe live ≈ Sharpe backtest ±0.3

### Phase 8 — Live ramp (6-12 mois)
- Capital initial $1k (3 mois)
- Si Sharpe live tient → $5k (3 mois)
- Si toujours tient → $10k+ (continuous scale)
- Continuous research : nouvelles features, model refresh mensuel
- **Gate** : Sharpe live >1, DD<20%, edge stable sur 6 mois

## 6. STACK TECHNIQUE FINAL

```
Recherche/Backtest  : Python 3.12 + Pandas/Polars + LightGBM + PyTorch + Optuna
ML pipeline         : MLflow (tracking) + Optuna (hyperparams) + DVC (data version)
Data storage        : ClickHouse (timeseries) + Parquet (cold) + Redis (state)
Execution           : Python orchestrator + Rust hot-path (latency critique)
Risk                : Riskfolio-Lib + custom VaR/CVaR + Monte Carlo (Numba)
Infrastructure      : Docker + K8s + Hetzner/OVH cloud (€100-200/mois)
Monitoring          : Grafana + Prometheus + Sentry + Slack/Telegram alerts
RL framework        : Stable-Baselines3 ou Ray RLlib pour execution agent
Production          : FastAPI (déjà) + Postgres state + WebSocket exchanges
```

## 7. PRÉ-REQUIS AVANT DE LANCER

1. **Capital** : minimum $5-10k pour absorber variance pendant 3 mois paper +
   6 mois live ramp. **Accepter perte 50% pendant validation.**
2. **Temps** : minimum 25-30h/sem dédiées sur 18-24 mois. Side-project 10h/sem
   = 3-4 ans.
3. **Apprentissage parallèle obligatoire** :
   - Marcos López de Prado *Advances in Financial Machine Learning* (2018)
   - Papers : Fama-French 1993, Jegadeesh-Titman 1993, Almgren-Chriss 2001,
     Bailey et al. 2014 (backtest overfitting probability), Gu-Kelly-Xiu
     (ML asset pricing)
   - Optionnel : Coursera "Machine Learning for Trading" Georgia Tech
4. **Discipline** : tolérance échec 70%+ probabilité Sharpe modeste (0.5-1.0),
   15-25% chance Sharpe>1.5, 5-10% fail total. **Pas garantie de profit.**
5. **Aplomb financier** : prêt à investir €100-200/mois infra cloud + capital
   live sans rentrée pendant 12-18 mois.

## 8. CONDITIONS DE LANCEMENT

Lancer Dexterio quant Niveau 3 SI **au moins une** de ces conditions :
1. HyperDex copy-trading Sharpe live <1.0 sur 3-6 mois validation
2. Quant gates HyperDex (funding, vol regime, momentum) testés et amélioration
   <30% PnL ou Sharpe <+0.3
3. Marché copy-trading HyperDex sature / cohorte se dégrade significativement
4. L'opérateur décide explicitement de pivoter (avec budget et temps requis)

**NE PAS lancer** si HyperDex confirme son edge live profitablement et que le
ROI temps/effort sur HyperDex reste supérieur.

## 9. PROCHAINE ÉTAPE SI LANCEMENT DÉCIDÉ

1. Lire ce doc + memory `project_dexterio_pivot_quant.md` (Claude)
2. Valider les 5 pré-requis (capital, temps, discipline, aplomb, apprentissage)
3. Démarrer Marcos López de Prado *Advances in Financial ML* en parallèle
4. Lancer Phase 0 (setup infra cloud) — 2 semaines
5. Audit complet du repo Dexterio actuel — identifier précisément quoi garder
   vs archiver
