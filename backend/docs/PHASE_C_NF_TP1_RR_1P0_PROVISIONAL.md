# PHASE C — News_Fade `tp1_rr` = 1.0R (candidat paper **provisoire**)

## Statut

- **Décision opérationnelle** : utiliser **1.0R** comme **premier objectif (TP1)** et **seuil `min_rr`** pour News_Fade en paper, en attendant confirmation sur d’autres fenêtres.
- **Non définitif** : ce réglage est **provisoire**. Il repose sur le mini-lab **nov2025** (PHASE B) et sur un arbitrage paper (plus de sorties TP réelles, moins de dépendance à `session_end`, comportement jugé plus exécutable vs 1.5R pour un écart de ΣR négligeable sur l’échantillon).
- **Révision** : toute dérive sur d’autres mois / régimes doit déclencher une réanalyse (voir plan de validation ci-dessous).

## Fondement (rappel PHASE B)

- **2.0R** : cible trop lointaine (sorties dominées par `session_end`, pas de TP1 sur l’échantillon).
- **1.25R** : pas de bénéfice clair vs 1.0R / 1.5R.
- **1.0R vs 1.5R** : performances globales très proches sur 27 trades NF ; **1.0R** privilégié pour paper par préférence explicite (plus de TP, moins de `session_end`).

Référence chiffrée : `results/labs/mini_week/_phase_b_nf_tp1_aggregate.json` et `docs/PHASE_B_NF_TP1_RR_SWEEP.md`.

## Mise à jour YAML canonique (NF only)

Fichier : `knowledge/playbooks.yml`, playbook **News_Fade** uniquement.

Champs modifiés sous `take_profit_logic` :

- `min_rr: 1.0`
- `tp1_rr: 1.0`

Non modifiés : `stop_loss_logic` (OPTION A, ±0,5 % moteur), `tp2_rr`, `breakeven_at_rr`, scoring, timefilters, contexte — **aucun autre playbook**.

## Plan de validation de confirmation (multi-fenêtres / multi-mois)

**Protocole opérationnel** : `docs/PHASE_1_NF_1R_CONFIRMATION_PROTOCOL.md` (presets `sep2025` / `oct2025` / `aug2025`, `--output-parent nf1r_confirm_*`, agrégateur `aggregate_nf_1r_confirmation.py`).

1. **Recopier le protocole PHASE B** (mini-lab semaine, SPY+QQQ, mêmes flags risk / LSS qu’au sweep) sur **au moins 2 mois calendaires supplémentaires** (ex. oct. 2025 + déc. 2025, ou T-1 / T-2 si données dispo), en utilisant le YAML canonique **après** PHASE C.
2. **Seuils de garde** (à adapter au volume de trades NF) :
   - expectancy R et ΣR NF **non dégradés** de façon matérielle vs nov2025 ;
   - part **TP1** reste **sensiblement supérieure** à un scénario type 1.5R sur la même fenêtre (comparaison A/B optionnelle en relançant un sweep ponctuel si doute).
3. **NY / LSS** : contrôler que le funnel `NY_Open_Reversal` (et LSS si pertinent) reste **aligné** avec les runs baseline de référence sur les mêmes fenêtres (pas de régression attendue : seul NF a changé).
4. **Critère de gel** : après **N ≥ 2** fenêtres mensuelles cohérentes, documenter « recommandation stable » ou rouvrir l’arbitrage 1.0R vs 1.5R si les métriques divergent.

## Commandes utiles

- Mini-lab une semaine (exemple) :

  ```bash
  cd backend && .venv/bin/python scripts/run_mini_lab_week.py \
    --start YYYY-MM-DD --end YYYY-MM-DD --label ma_feneture
  ```

- Multi-semaines prédéfini :

  ```bash
  cd backend && .venv/bin/python scripts/run_mini_lab_multiweek.py --preset nov2025
  ```

Pour une comparaison structurée NF-only sur plusieurs `tp1_rr`, réutiliser `scripts/run_mini_lab_phase_b_nf_tp1_sweep.py` (PHASE B) en pointant vers des YAML dérivés ou en dupliquant la logique d’agrégation.
