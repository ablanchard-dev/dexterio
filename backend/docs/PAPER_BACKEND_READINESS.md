# Paper backend — readiness (état réel DexterioBOT)

## Gate : **PAPER_READY_SUPERVISED**

Le backend permet un **paper supervisé** (runs batch, artefacts, agrégats) avec **garde-fous risk** documentés. Il manque des pièces pour un paper 24/7 **non supervisé** (reprise session, API unifiée, alertes).

## Couvert (preuve repo)

| Domaine | État | Fichiers / scripts |
|---------|------|-------------------|
| Runners mini-lab | OK | `scripts/run_mini_lab_week.py`, `run_mini_lab_multiweek.py` |
| Nomenclature runs | OK | `run_id`, `output-parent`, `mini_lab_summary_*.json` |
| Artefacts | OK | `results/labs/mini_week/...`, parquets trades, debug_counts |
| Agrégats playbook | OK | `aggregate_mini_lab_summaries.py`, `aggregate_nf_1r_confirmation.py`, PHASE B aggregate |
| Garde-fous risk | OK | `risk_engine.py`, env `RISK_EVAL_*` (mini-lab) |
| Journal trades (export) | Partiel | Parquet trades par run ; `TradeJournal` global souvent neutralisé en lab (`_save` noop) |
| Reprise / redémarrage session | **Manquant** | Pas de service long-running stateful documenté |
| Monitoring / alertes | **Manquant** | Pas de hook standardisé hors logs |

## Checklist paper supervisé

- [x] Lancer un run reproductible avec mêmes flags risk.
- [x] Séparer campagnes (`output-parent`) sans écraser baseline.
- [x] Lire funnel NY/NF/LSS depuis `mini_lab_summary`.
- [x] Agréger NF (confirmation 1.0R) via script dédié.
- [ ] Reprise après crash : **à concevoir** (checkpoint run_id, idempotence).
- [ ] Endpoint HTTP unique « état paper » : **hors scope actuel** (front plus tard).

## Patchs backend faible rayon (recommandés plus tard)

- Option : activer écriture journal parquet contrôlée en lab (flag) pour aligner avec futur contrat front.
- Option : `run_manifest.json` par campagne (git_sha, commande, preset).

## Rollback

Revenir aux scripts / env documentés dans les docs PHASE ; aucun patch obligatoire dans ce fichier.
