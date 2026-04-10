# Paper Trading Plan (Wave 1)

## Objectif
- Construire une **première vague paper** à partir des meilleurs playbooks du labo 24m.
- Politique de sélection: agressive, classement principal `total_R_net`.

## Pipeline
- Agréger: `python backend/scripts/aggregate_full_playbooks_lab.py --top-n 8 --min-trades 25 --min-pf 1.0`.
- Sorties:
  - `backend/results/playbooks_leaderboard_24m.json`
  - `backend/results/playbooks_wave1_candidates.json`
  - `backend/knowledge/paper_wave1_playbooks.yaml`

## Activation runtime paper
- Configurer:
  - `PAPER_USE_WAVE1_PLAYBOOKS=true`
  - `PAPER_WAVE1_PLAYBOOKS_FILE=backend/knowledge/paper_wave1_playbooks.yaml`
- Le `RiskEngine` autorise alors uniquement les playbooks Wave 1 (hors mode labo backtest).

## Gate paper minimal
- Durée minimale: 20 sessions paper.
- Drawdown max paper: -8R.
- Drift vs backtest toléré: `|R_paper - R_backtest| <= 35%`.
- Retrait playbook: 2 semaines négatives consécutives ou PF paper < 0.9 sur 30 trades.

## Phase 3 (après gate P2 / LSS exécutable en lab)
- Contenu Wave 1 figé dans `backend/knowledge/paper_wave1_playbooks.yaml` : `NY_Open_Reversal`, `News_Fade`, `Liquidity_Sweep_Scalp` (métriques de référence : lab Nov 2025 SPY+QQQ avec flag P2 sur le runner).
- Activer `PAPER_USE_WAVE1_PLAYBOOKS=true` : le runtime paper n’autorise que ces playbooks **et** la quarantaine dynamique YAML ne les bloque plus (la denylist statique `AGGRESSIVE_DENYLIST` reste appliquée).
- Le flag lab `RISK_BYPASS_DYNAMIC_QUARANTINE_LSS_ONLY` reste disponible pour les backtests sans Wave 1 ; en paper Wave 1, LSS est couvert par l’exception Wave 1 ci-dessus.

## Phase 3B — exécution (alignement paper/backtest Wave 1)

- Sémantique : breakeven au RR YAML, time-stop LSS 30 min, `session_end` NY/NF — voir **`backend/docs/PHASE_3B_COMPARABILITY.md`**.
- **Important :** ce n’est pas un micro-fix sans effet sur l’historique. Les agrégats R et les `exit_reason` pour **NY** et **News_Fade** ne sont **pas comparables** aux runs d’avant 3B sans re-baseline explicite ; documenter toute comparaison temporelle en conséquence.

## Phase 4 (suite)

- Après validation post-3B et archivage des artefacts comparatifs : enchaîner sur **Phase 4 / audit D27** (périmètre et critères à figer au moment du lancement d’audit).

