# Échelle de campagnes backtest Dexterio (ladder)

**Réconciliation roadmaps :** lire d’abord `docs/ROADMAP_DEXTERIO_TRUTH.md` (vérité unique des axes DexterioBOT).

Objectif : **itération rapide** puis **validation longue** sans se mentir sur la couverture data ni sur les gates playbooks.

Compatible avec : `run_mini_lab_week.py`, `run_mini_lab_multiweek.py`, `backtest_data_preflight.py`, manifests, analyzer bundle, `scripts/campaign_gate_verdict.py`.

## Outils (post–`DataCoverageV0` manifest)

| Outil | Rôle | Ladder |
|--------|------|--------|
| `run_manifest.json` → `data_coverage` | Preuve couverture parquet vs `[start,end]` + warmup (même logique que preflight) | ≥ micro-lab ; **obligatoire** avant ≥ 1 mois si `--strict-manifest-coverage` |
| `scripts/compare_mini_lab_summaries.py` | Diff JSON entre deux `mini_lab_summary_*.json` (funnel, `total_trades`, `final_capital`) | Tous niveaux après deux runs |
| `scripts/walk_forward_light.py` | 2 splits OOS + train expanding (calendrier seul) | ≥ lab 1 mois / validation 3–24 mois |
| `scripts/run_walk_forward_mini_lab.py` | Enchaîne `run_mini_lab_week` par fenêtre (sous-processus) + `walk_forward_campaign.json` | ≥ lab 1 mois |
| `mini_lab_summary.trade_metrics_parquet` | `expectancy_r` / `sum_pnl_dollars` depuis parquet trades post-run | Tous niveaux (compare exploitable) |
| `scripts/backtest_leakage_audit.py` | Trades `entry<=exit`, OHLCV monotone, option coverage fenêtre | ≥ validation 3 mois (batch CI / manuel) |
| `scripts/campaign_gate_verdict.py` | Verdict déclaratif `NOT_READY` / `BACKTEST_READY…` / `LIMITED_PAPER…` (JSON) ; `--manifest-only` si pas de summary | Après chaque run « promotion » |
| `scripts/backtest_campaign_smoke.py` | Pytest ciblé outils campagne (+ preflight optionnel via env) | CI / avant PR campagne |

## Contrat opérationnel par niveau (exécutable)

| Niveau | Objectif | Artefacts obligatoires | Checks obligatoires | Seuil qualité min | Playbooks autorisés (défaut) | Passage niveau suivant |
|--------|----------|------------------------|---------------------|-------------------|------------------------------|------------------------|
| **1 jour** | Smoke moteur + slice data | logs ; `mini_lab_summary` si script semaine raccourci ; ou debug_counts équivalent | `backtest_data_preflight` OU `data_coverage_ok` dans manifest si mini-lab | Pas d’exception ; slice non vide | Tout ce qui est déjà en allowlist **ou** run isolé playbook | 1 semaine stable |
| **1 semaine** | Funnel reproductible | `mini_lab_summary_*.json`, `run_manifest.json`, parquet trades | `data_coverage` manifest ; option `--strict-manifest-coverage` | Funnel non nul pour au moins un playbook cible ; `git_sha` présent | Noyau : NY, LSS, FVG, Session ; NF seulement si YAML figé campagne | 4 semaines cohérentes |
| **1 mois** | Stabilité courte | 4× artefacts semaine **ou** run custom + agrégat (`aggregate_mini_lab_summaries` / JSON maison) | Preflight sur union des dates ; `compare_mini_lab_summaries` entre semaines | Pas de contradiction majeure funnel vs parquet | Idem semaine ; **pas** de YAML NF ad-hoc non versionné | 3 mois OOS planifié |
| **3 mois** | 1ʳᵉ courbe R intermédiaire | Dossier `output-parent` ; tous manifests ; WF optionnel (`run_walk_forward_mini_lab`) | `backtest_data_preflight` **strict** ; `backtest_leakage_audit` trades+data | `campaign_gate_verdict` ≠ `NOT_READY` avec options strictes négociées | Uniquement allowlist **sans** deny ; **exclure** sweeps tp1 / Wave2 expérimental des agrégats « noyau » | 6 mois |
| **6 mois** | Régimes multiples | 2× blocs 3 mois + comparaison | Même que 3 mois + compare inter-blocs | Robustesse (pas un seul mois porteur) | Idem 3 mois | 1 an |
| **1 an** | Gate sérieux paper élargi | Campagne unique + tables/agrégats | OOS documenté ; coûts moteur actifs dans les runs | Drawdown / R interprétables (hors ce doc) | Noyau stable uniquement | 2 ans **ou** paper limité si gate |
| **2 ans** | Stress long | Idem 1 an ×2 ou calendrier continu | Anti-leakage + qualité data | Pas de sursimulation évidente | Même noyau ; **Trend_Continuation** / A+ deny **hors** promo | Paper limité **seulement** si verdict + scope produit |

Commandes types : preflight et gate —

```bash
.venv/bin/python scripts/backtest_data_preflight.py --start A --end B --warmup-days 30
.venv/bin/python scripts/campaign_gate_verdict.py path/mini_lab_summary_*.json --manifest path/run_manifest.json \\
  --require-manifest-coverage --require-trade-metrics
```

## Niveaux (vue courte)

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
