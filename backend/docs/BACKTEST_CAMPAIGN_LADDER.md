# Échelle de campagnes backtest Dexterio (ladder)

Objectif : **itération rapide** puis **validation longue** sans se mentir sur la couverture data ni sur les gates playbooks.

Compatible avec : `run_mini_lab_week.py`, `run_mini_lab_multiweek.py`, `backtest_data_preflight.py`, manifests, analyzer bundle.

## Outils (post–`DataCoverageV0` manifest)

| Outil | Rôle | Ladder |
|--------|------|--------|
| `run_manifest.json` → `data_coverage` | Preuve couverture parquet vs `[start,end]` + warmup (même logique que preflight) | ≥ micro-lab ; **obligatoire** avant ≥ 1 mois si `--strict-manifest-coverage` |
| `scripts/compare_mini_lab_summaries.py` | Diff JSON entre deux `mini_lab_summary_*.json` (funnel, `total_trades`, `final_capital`) | Tous niveaux après deux runs |
| `scripts/walk_forward_light.py` | 2 splits OOS + train expanding (calendrier seul) | ≥ lab 1 mois / validation 3–24 mois |
| `scripts/backtest_leakage_audit.py` | Trades `entry<=exit`, OHLCV monotone, option coverage fenêtre | ≥ validation 3 mois (batch CI / manuel) |

## Niveaux

| Niveau | Fenêtre type | Objectif | Coût CPU | Artefacts minimum | Réussite | Échec | Promotion |
|--------|----------------|----------|----------|-------------------|----------|-------|-----------|
| **Smoke 1 jour** | 1 session / 1j | Sanity moteur + data | Très faible | logs, 0 trade OK | Pas d’exception ; data slice non vide | Crash / slice vide | → micro-lab |
| **Micro-lab 1 semaine** | `run_mini_lab_week` | Funnel + 1 playbook ciblé | Faible | `mini_lab_summary`, `run_manifest`, parquet trades | Funnel cohérent ; pas de régression NY (surveillance) | Empty slice ; NY funnel effondré | → lab 1 mois |
| **Lab 1 mois** | 4×1 semaine ou run custom | Stabilité stats courtes | Moyen | idem + agrégats optionnels | Métriques stables vs smoke | Variance seule → pas concluant | → 3 mois |
| **Validation 3 mois** | ~13 semaines | Première courbe R crédible intermédiaire | Élevé | campagne `output-parent`, manifests | Couverture data OK (`backtest_data_preflight`) | Trous data ; playbook contradictoire policy | → 6 mois |
| **Validation 6 mois** | 2×3 mois | Régimes multiples | Très élevé | idem | Robustesse vs 3m | Sensible à un seul mois | → 1 an |
| **Validation produit 1 an** | calendrier 52s | Gate « sérieux » avant paper élargi | Très élevé | agrégats + tables | R / drawdown interprétables | Data incomplète sur 1 an | → 2 ans ou paper **limité** |
| **Validation robuste 2 ans** | 104 sem. | Stress régimes + liquidité | Max | idem + comparaisons | Stabilité sous stress | Sursimulation / data biaisée | → paper limité **seulement** si gates OK |

## Preflight obligatoire avant ≥ 1 mois

```bash
cd backend
.venv/bin/python scripts/backtest_data_preflight.py --start YYYY-MM-DD --end YYYY-MM-DD --warmup-days 30
```

Chaque run `run_mini_lab_week` enregistre la même vérification dans `run_manifest.json` sous `data_coverage` (et des champs résumés dans `mini_lab_summary_*.json`). Utiliser `--strict-manifest-coverage` pour **bloquer** un run si la couverture est insuffisante.

## Gates playbooks (rappel)

- **Denylist / quarantaine** : ne pas polluer les agrégats « noyau » avec playbooks exclus (`risk_engine.py`, `playbook_quarantine.yaml`).
- **NF** : pas de YAML canonique tant que gate tp1 non tranché.

## Portefeuille playbooks × niveau (campagne uniquement)

| Niveau | Playbooks « noyau » recommandés | À exclure / isoler des validations longues |
|--------|----------------------------------|---------------------------------------------|
| Smoke 1j / micro-lab 1 sem | NY, LSS (scalp), FVG/Session si déjà en allowlist | Tout playbook en quarantaine / deny |
| Lab 1 mois | + News_Fade **si** YAML figé pour la campagne | Variantes YAML ad-hoc non versionnées |
| Validation 3–24 mois | Uniquement playbooks **stables** et documentés dans le manifest (`playbooks_yaml`, `git_sha`) | Playbooks expérimentaux Wave 2, sweeps tp1, toute entrée non alignée `risk_engine` + `playbook_quarantine` |

Les outils **compare** / **walk-forward** / **leakage audit** ne changent pas les playbooks : ils rendent les campagnes **auditables** à chaque marche de l’échelle.

## Paper

Aucun niveau de ce ladder **n’implique** paper automatiquement. Gate honnête : **LIMITED_PAPER_READY_IF_SCOPE_REDUCED** après validation intermédiaire + périmètre explicite.
