# Live Deployment Plan (Post Gate 3)

## Prérequis avant live
- Gate backtest validé (labo 24m + leaderboard versionné).
- Gate paper validé (durée mini, drawdown, drift, règles de retrait).
- IBKR connectivité validée via `GET /api/trading/ibkr-connection`.

## Politique de promotion vers live
- Démarrage progressif avec sous-ensemble Wave 1 (Top-3).
- Taille de risque live réduite (50% du risque paper).
- Ajout incrémental des playbooks selon performance live observée.

## Conditions de rollback
- Drawdown live > seuil autorisé.
- Erreurs d'exécution répétées (broker/data/routing).
- Divergence marquée des métriques vs paper.

## Observabilité
- Vérifier quotidiennement:
  - métriques de risque (`risk_engine_stats_*`),
  - état playbooks (`playbook_stats_*`),
  - logs d'exécution.

