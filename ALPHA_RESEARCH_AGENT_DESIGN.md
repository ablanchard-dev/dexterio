# Dexterio v3 — Alpha Research Agent (multi-agents IA)

**Date** : 2026-05-25
**Statut** : DESIGN — pas encore lancé
**Évolution** : pivot de "bot quant niveau 3 exec" (v1 du plan) vers
"système autonome de génération+test d'hypothèses d'alpha" (v3 actuel).

Ce doc complète et **remplace** la vision de
`PIVOT_QUANT_LEVEL_3_PLAN.md` (qui reste valide pour la couche
backtest+exec mais n'est plus l'objectif final).

---

## 1. VISION

Pas un bot de trading classique. Un **laboratoire quant assisté IA** :

```
Données → IA cherche patterns/hypothèses → formalisation mathématique
→ backtests robustes → validation → amélioration → nouvelle génération
```

Inspiration :
- **Sakana AI Scientist** (arXiv 2408.06292) — démontre que la boucle
  "hypothèse → expérience → résultat → itération" fonctionne en ML research
  via LLM. Adaptable à finance.
- **JEPA / I-JEPA** (arXiv 2301.08243) — Joint-Embedding Predictive
  Architecture, self-supervised representation learning. Adaptable à
  séries temporelles marchés (Market-JEPA / Temporal-JEPA).

L'objectif n'est pas que l'IA dise "Achète maintenant". L'objectif est
qu'elle dise :

> "Voici 12 hypothèses plausibles. Voici pourquoi elles pourraient exister.
> Voici comment les tester. Voici les variables. Voici les risques de biais.
> Voici les conditions de rejet."

L'arbitre final reste le **Validation Engine**, pas le LLM.

## 2. ARCHITECTURE MULTI-AGENTS

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Data Agent          → nettoie, vérifie, enrichit         │
│ 2. Pattern Agent       → cherche anomalies, régimes, corr   │
│ 3. Hypothesis Agent    → génère hypothèses structurées (LLM)│
│ 4. Formalization Agent → convertit en règles testables / ML │
│ 5. Experiment Agent    → backtests, splits, walk-forward    │
│ 6. CRITIC Agent ★      → biais : look-ahead, overfit, snoop │
│ 7. Edge Scorer         → classe par robustesse/profit/risque│
│ 8. Mutation Agent      → améliore hypothèses prometteuses   │
│ 9. Research Memory     → stocke testé/rejeté/validé/modifié │
│ 10. Human Review       → opérateur valide décisions clés    │
└─────────────────────────────────────────────────────────────┘

Boucle :
[Data] → [Pattern Discovery] → [Hypothesis Generator] →
[Strategy Formalizer] → [Backtest Engine] → [Validation Engine] →
[Edge Scoring] → [Research Memory] → [Hypothesis Mutation/Upgrade] → recommence
```

Le CRITIC Agent est **le plus important**. Sans Critic strict, le système
devient une machine à faux edges (générer 10000 hypothèses → garder les 5
"chanceuses" = data snooping géant).

## 3. RÔLE DU LLM

**Le LLM ne décide PAS de trader.** Il est :
- Chercheur (génère hypothèses)
- Brainstormer (combine idées de familles différentes)
- Analyste (lit rapports, news)
- Traducteur intuition → protocole de test
- Proposeur de features
- Explicateur de résultats
- Détecteur d'incohérences méthodologiques
- Producteur de rapports

Mais :
- LLM ne fait PAS de validation statistique (= rôle Validation Engine)
- LLM ne décide PAS du sizing (= rôle Risk Engine)
- LLM ne déclenche PAS de trade live (= rôle Human Review + Execution Layer)

## 4. FORMAT OBLIGATOIRE DES HYPOTHÈSES (DSL)

Chaque hypothèse stockée en **YAML structuré strict**. Exemple :

```yaml
hypothesis_id: HYP_2026_000123
name: "Post-CPI Nasdaq continuation after downside surprise"
market: "NQ / QQQ"
family: "event_driven_momentum"
rationale: "Lower CPI may trigger rates repricing and equity risk-on flow."

event_trigger:
  type: "macro"
  event: "CPI"
  surprise_direction: "below_consensus"
  surprise_threshold: "-0.2"

entry_logic:
  timeframe: "5m"
  condition:
    - "price breaks first_15m_high"
    - "volume_zscore > 1.5"
    - "vwap_distance between 0 and 1.2 ATR"

exit_logic:
  stop: "1.0 ATR"
  take_profit: "2.0 ATR"
  time_stop: "120 minutes"

risk:
  max_risk_per_trade: "0.5%"

validation_plan:
  train_period: "2018-2022"
  validation_period: "2023-2024"
  test_period: "2025-2026"

failure_conditions:
  - "expectancy_after_cost <= 0"
  - "max_drawdown > 15%"
  - "performance only explained by one year"
  - "slippage destroys edge"
```

Forcer le LLM à produire **dans ce DSL**. Pas de free-text vague.

## 5. FAMILLES D'HYPOTHÈSES À COUVRIR

| Famille | Exemple type |
|---|---|
| Momentum intraday | Breakout post-news, continuation post-impulsion |
| Mean reversion | Excès → retour VWAP |
| Volatilité | Compression → expansion |
| Microstructure | Déséquilibre orderbook → mouvement court terme |
| Event-driven | CPI, FOMC, earnings, ETF, régulation |
| Cross-asset | Taux→Nasdaq, dollar→or, pétrole→énergie |
| Regime-based | Strat active seulement en tendance ou haute vol |
| Seasonality | Effets horaires, jours, fin de mois |
| Sentiment | News/social/transcripts → réaction retardée |
| Options/futures | Gamma, open interest, funding, liquidations |
| Prediction markets | Erreurs probabilité implicite, biais foule |
| Wallet/flow tracking | Smart wallets, whales, comportements récurrents |

## 6. STACK ML

### A. Modèles statistiques classiques (Phase 1+)
Regression linéaire/logistique, ARIMA/GARCH, cointégration, factor models,
tests hypothèse, bootstrap, Monte Carlo, clustering régimes. Donnent
lisibilité.

### B. ML tabulaire (Phase 2+)
Random Forest, LightGBM/XGBoost, CatBoost, Elastic Net, ranking models,
calibration probabilité, SHAP feature importance. Sweet spot recherche
alpha.

### C. Deep learning temporel (Phase 3+)
LSTM/GRU, Temporal Convolutional Networks, Transformers temporels,
attention multi-actifs, autoencoders, contrastive learning, self-supervised.

### D. JEPA / world models (Phase 4 R&D)
Market-JEPA / Temporal-JEPA : prédire état latent futur du marché plutôt
que prix exact. Embeddings de régime, clustering contextes, génération
d'hypothèses depuis états latents.

Au lieu de "prix dans 10 min = X", prédiction :
- Régime volatilité probable
- Probabilité breakout
- Risque mean reversion
- Compression/expansion
- Stress liquidity
- Anomalie de flux

## 7. NIVEAUX D'AUTONOMIE

| Niveau | Description | V cible |
|---|---|---|
| 1 | Recherche assistée : humain propose, système teste | (déjà existant en partie) |
| 2 | Génération d'hypothèses : système propose lui-même | V1 cible Alpha Research Agent |
| 3 | Boucle autonome de recherche : génère/teste/comprend échecs/modifie/combine/améliore | V2 cible ultime |

Niveau 3 ≠ "live automatique". Niveau 3 = **recherche autonome d'alpha**
avec validation stricte. Live = jamais autonome, toujours humain valide.

Progression suggérée :
- **A** : IA propose, humain valide
- **B** : IA teste seule, humain valide candidats
- **C** : IA modifie seule les hypothèses
- D : IA peut lancer paper seule (NON V1)
- E : IA peut lancer live seule (JAMAIS)

V1 recommandé : **A → B → C** progressif. Pas D/E au début.

## 8. CRITIC AGENT — LE COEUR DU SYSTÈME

11 gates obligatoires par hypothèse avant promotion :

| Gate | Question |
|---|---|
| Plausibilité économique | Pourquoi cet edge devrait exister ? |
| Données suffisantes | Assez d'échantillons ? |
| Pas de fuite temporelle | Info disponible au moment du trade ? |
| Coûts réalistes | Frais/spread/slippage inclus ? |
| Out-of-sample | Marche sur données non vues ? |
| Walk-forward | Stable dans le temps ? |
| Robustesse paramètres | Pas dépendant d'un réglage exact ? |
| Robustesse régime | Marche dans plusieurs contextes ? |
| Capacité | Peut-on l'exécuter avec taille réelle ? |
| Décorrélation | Apporte quelque chose au portefeuille ? |
| Paper validation | Le réel ressemble au backtest ? |

Si hypothèse échoue : **stockée en Research Memory avec raison du rejet**
(pas perdue, devient input pour Mutation Agent).

**Bonferroni correction** : si N hypothèses testées, seuil significance =
α/N. Si on teste 10000 hypothèses avec α=0.05 → seuil = 0.000005. Très
strict mais nécessaire pour éviter false discoveries.

**Bayesian Probability of Backtest Overfitting** (Bailey-López de Prado
2014) : calcule probabilité que la stratégie soit overfit. Si PBO > 0.5
= rejet automatique.

## 9. CYCLE MUTATION D'UNE HYPOTHÈSE

```
Hypothèse brute (LLM génère)
  → test global (Experiment Agent)
  → résultat négatif global ?
  → analyse par sous-régime (Critic Agent décompose)
  → identifie : positif uniquement quand VIX<22 ET surprise CPI<-0.2
  → Mutation Agent ajoute filtre régime vol + filtre surprise
  → re-test (Experiment Agent)
  → validation out-of-sample (Critic Agent)
  → promotion vers paper OU rejet définitif
```

Une hypothèse échouée n'est jamais perdue. Elle devient **input pour
améliorations futures**.

## 10. PHASES DE DÉVELOPPEMENT

### Phase 1 — Alpha Research Loop simple (8-12 sem)
- LLM (Hypothesis Agent) génère hypothèses structurées YAML
- Backtest engine teste (réutilise engine Dexterio existant)
- Validation engine note (Sharpe, PF, MDD, PBO)
- Research memory stocke tout
- Critic Agent v1 (10 gates de base)
- Human Review pour promotion paper

**Output** : preuve du concept end-to-end. 100-500 hypothèses testées, 0-2
candidates paper validées.

### Phase 2 — Auto-feature engineering (8-12 sem)
- AutoML / AutoFE pour automatiser sélection, transformation, génération de
  features (réf : ScienceDirect AutoFE papers)
- Le système crée features, teste transformations/interactions/régimes
- Classe features selon pouvoir prédictif (SHAP, mutual information)

**Output** : 100→1000+ features candidates, top 50 retenues par stabilité +
pouvoir prédictif.

### Phase 3 — ML alpha models (12-16 sem)
- Modèles tabulaires (LightGBM, CatBoost)
- Modèles temporels (LSTM, TCN)
- Classification de setups (régression logistique calibrée)
- Prédiction de régime
- Ranking de trades cross-sectional

**Output** : modèles ML intégrés au pipeline, alpha signaux générés par
ML+LLM ensemble.

### Phase 4 — JEPA / latent world model (24+ sem R&D)
- Self-supervised learning sur séquences marché
- Market-JEPA : embeddings de régime
- Prédiction d'état latent futur
- Clustering contextes
- Génération d'hypothèses depuis états latents

**Output** : R&D pure, pas garantie de succès. Si ça marche = breakthrough.

## 11. DONNÉES NÉCESSAIRES

| Type | Utilité | Priorité |
|---|---|---|
| OHLCV multi-TF | Base backtest | V1 |
| Intraday 1m/5m | Setups précis | V1 |
| Tick / order book L2 | Microstructure | V2 |
| Futures | Macro, indices, commodities | V1-V2 |
| Options | IV, Greeks, smile/skew | V2 |
| News (RSS/API) | Event-driven | V1 |
| Calendrier macro | CPI, FOMC, NFP, PMI | V1 |
| Earnings | Surprises, guidance | V2 |
| Sentiment social | Twitter, Reddit, transcripts | V2 |
| Cross-asset | Taux, dollar, or, pétrole, VIX | V1 |
| Broker fills (paper/live) | Comparer backtest/réel | V1 (paper) |
| Journal stratégie | Mémoire recherche | V1 |

## 12. STACK TECHNIQUE

```
Recherche      : Python 3.12 + Pandas/Polars + LightGBM + PyTorch
                 + Optuna + scikit-learn
LLM            : API (Claude/GPT-4) en V1, local (Llama/Qwen) en V2
                 hybride possible (LLM API pour Hypothesis, local pour analysis)
Multi-agents   : framework LangGraph ou AutoGen pour orchestration
ML tracking    : MLflow + DVC (data versioning)
Backtest       : Engine Dexterio existant (réutilisé, refondu pour DSL hyp)
Data storage   : ClickHouse (timeseries) + Parquet (cold) + Redis (state)
Execution      : Python paper V1 → Rust hot-path V3 si live latency-critique
Risk           : Riskfolio-Lib + custom VaR/CVaR + Monte Carlo (Numba)
Infrastructure : Docker + Hetzner/OVH (€100-200/mois cloud)
Monitoring     : Grafana + Prometheus + Sentry + Slack/Telegram alerts
UI             : FastAPI (déjà Dexterio) + React (frontend recherche)
```

## 13. 7 DÉCISIONS STRUCTURANTES (À TRANCHER AVANT CAHIER DES CHARGES)

Avant écrire le doc spec complet :

1. **Marché V1** : actions/ETF US, futures, crypto, Polymarket ?
   _Reco : 1 seul univers principal. Crypto perp suggéré (cohérent avec
   HyperDex infrastructure)._

2. **Horizon V1** : intraday, swing, event-driven, daily, prediction markets ?
   _Reco : event-driven + intraday/swing._

3. **Mode V1** : recherche seule, backtest, paper, ou paper exec déjà ?
   _Reco : recherche + backtest + paper. Pas live V1._

4. **Budget data** : 0€, faible coût, ou APIs premium plus tard ?
   _Reco : faible coût (€50-200/mois)._

5. **LLM** : API externe, modèle local, ou hybride ?
   _Reco : API en V1 (Claude/GPT-4), hybride V2 (local Llama pour analyse,
   API pour génération créative)._

6. **Objectif final** : outil personnel privé, future app SaaS, autre ?
   _Reco : V1 personnel, ouvert à SaaS futur si edge prouvé._

7. **Priorité IA** : LLM hypothesis engine d'abord, ou ML/JEPA recherche
   d'abord ?
   _Reco : LLM hypothesis Phase 1, AutoFE/ML Phase 2-3, JEPA Phase 4 R&D._

## 14. CONDITIONS DE LANCEMENT (RAPPEL)

Lancer SI au moins une de ces conditions (cf
`PIVOT_QUANT_LEVEL_3_PLAN.md` section 8) :
1. HyperDex Sharpe live <1.0 sur 3-6 mois
2. Quant gates HyperDex testés et amélioration <30% PnL ou Sharpe <+0.3
3. Cohorte HyperDex sature/dégrade
4. Décision opérateur explicite (avec budget + temps validés)

## 15. PRÉ-REQUIS

Avant Phase 1 :
- **Capital** : $5-10k minimum (live ramp). Acceptation perte 50% pendant
  validation.
- **Temps** : 25-30h/sem sur 24-36 mois (full focus). Side-project = 4-6 ans.
- **Coût récurrent** : €100-300/mois (infra + LLM API + data)
- **Apprentissage parallèle obligatoire** :
  - Marcos López de Prado *Advances in Financial Machine Learning* (2018)
  - Papers : Sakana AI Scientist, I-JEPA, Almgren-Chriss, Bailey PBO,
    Gu-Kelly-Xiu ML asset pricing, Bailey-López de Prado backtest overfit
- **Discipline** : tolérance échec élevée. 5-15% chance Sharpe live >1.5
  réel. 50-70% chance Sharpe modeste. 15-30% fail total.
- **Aplomb financier** : pas de rentrée pendant 18-24 mois.

## 16. ASSET RÉUTILISABLE DE DEXTERIO V1

| Composant Dexterio actuel | Statut pivot v3 |
|---|---|
| `backtest/engine.py` Phase 2.3 | ✅ Garder (backbone) |
| `backtest/costs.py` IBKR + slippage | ✅ Garder + étendre crypto perp fees |
| `backtest/metrics.py` | ✅ Garder + ajouter PBO Bayesian |
| `engines/stat_arb/` | ✅ Garder + intégrer dans Hypothesis families |
| `engines/regime/classifier.py` | ✅ Garder + étendre features Pattern Agent |
| `engines/features/` (11 features) | ✅ Garder, étendre via AutoFE |
| `research/feature_store.py` | ✅ Garder + scaler 100→10000+ |
| `research/label_factory.py` | ✅ Garder + triple-barrier |
| `research/quality_report.py` | ✅ Garder + intégrer dans Critic Agent |
| `risk_engine.py` | ✅ Garder + étendre VaR/CVaR Monte Carlo |
| `execution/paper_trading.py` | ✅ Garder |
| `engines/patterns/` ICT/SMC | ❌ Archive (LLM remplace, ne dépend plus de patterns hardcoded) |
| `engines/setup_engine*.py` | ❌ Archive |
| `engines/aplus01_driver.py`, `smt_driver.py` | ❌ Archive |

**Asset stratégique conservé** : ~60% du code Dexterio reste valide. La
refonte porte sur la couche **génération + sélection de stratégies**, qui
passe de "humain code → backtest" à "LLM génère hypothèses → Critic valide →
Backtest teste → Mutation améliore".

## 17. PROCHAINES ÉTAPES SI LANCEMENT DÉCIDÉ

1. **Décider les 7 questions structurantes** (section 13) avec opérateur
2. **Valider 5 pré-requis** (section 15)
3. **Commander Marcos López de Prado** *Advances in Financial ML* + lire
   chapitres 1-7 (~2 semaines)
4. **Phase 0** : setup infra cloud + audit complet repo Dexterio (3 sem)
5. **Phase 1** : Alpha Research Loop simple (8-12 sem)
6. **Gate Phase 1** : démontrer 1-2 hypothèses validées avec PBO<0.1,
   Sharpe holdout>1.0. Sinon : abandon, retour HyperDex.

---

**Référence externe** :
- Sakana AI Scientist : https://arxiv.org/abs/2408.06292
- I-JEPA : https://arxiv.org/abs/2301.08243
- Bailey-López de Prado PBO : https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf
- Almgren-Chriss optimal execution : https://ideas.repec.org/a/rsk/journ4/2161150.html
- Gu-Kelly-Xiu ML asset pricing : (chercher via Google Scholar)
