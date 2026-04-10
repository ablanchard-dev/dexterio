# EDGE Experiment Protocol

Objectif: améliorer l'edge sans rouvrir le chaos.

## Règles non négociables

- Un seul playbook expérimenté à la fois.
- Pas de changement sur `NY_Open_Reversal` (logique métier).
- Pas de réactivation de `Trend_Continuation_FVG_Retest` sans triage explicite.
- Pas de desserrage global des filtres edge.

## Template d'expérience

## 1) Hypothèse

- Playbook ciblé:
- Problème observé:
- Hypothèse edge:

## 2) Changement minimal

- Fichiers touchés:
- Paramètre(s) modifié(s):
- Pourquoi ce patch est minimal:

## 3) Fenêtre de test

- Run court (sanity rapide):
- Run labo (1 mois minimum):
- Référence de comparaison:

## 4) Métriques de succès

- trades total (éviter floodgate)
- expectancy R
- profit factor
- hit rate
- drawdown R
- part des trades en chop
- % trades avec sweep (si SCALP)
- invariants (`post_run_verification.pass`)

## 5) Critères d'arrêt

- Stop immédiat si invariants cassés.
- Stop si expectancy dégradée fortement (> 30% vs référence).
- Stop si volume explose sans amélioration qualité.

## 6) Décision

- `KEEP`: edge robuste + invariants OK + amélioration stable.
- `REFINE`: signaux contradictoires, besoin patch ciblé.
- `KILL`: dégradation nette ou risque opérationnel.

## 7) Artefacts obligatoires

- `summary_*`
- `sanity_report_*`
- `post_run_verification_*`
- `structural_diagnostics_*`
- `learning_snapshot_*`
- `playbook_triage_*`
