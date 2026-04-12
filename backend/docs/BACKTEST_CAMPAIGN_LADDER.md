# Échelle de campagnes backtest Dexterio (ladder)

Objectif : **itération rapide** puis **validation longue** sans se mentir sur la couverture data ni sur les gates playbooks.

Compatible avec : `run_mini_lab_week.py`, `run_mini_lab_multiweek.py`, `backtest_data_preflight.py`, manifests, analyzer bundle.

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

## Gates playbooks (rappel)

- **Denylist / quarantaine** : ne pas polluer les agrégats « noyau » avec playbooks exclus (`risk_engine.py`, `playbook_quarantine.yaml`).
- **NF** : pas de YAML canonique tant que gate tp1 non tranché.

## Paper

Aucun niveau de ce ladder **n’implique** paper automatiquement. Gate honnête : **LIMITED_PAPER_READY_IF_SCOPE_REDUCED** après validation intermédiaire + périmètre explicite.
