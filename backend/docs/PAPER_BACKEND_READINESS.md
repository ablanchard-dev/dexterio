# Paper backend — readiness (état réel DexterioBOT)

## Gate : **PAPER_READY_SUPERVISED_HARDENED**

Le backend permet un **paper supervisé** avec **traçabilité renforcée** : chaque `run_mini_lab_week` émet désormais `contract_version` + `run_started_at_utc` dans le summary et un fichier **`run_manifest.json`** (commande, `cwd`, `git_sha`, `output_parent`).  
Il manque encore : **reprise 24/7**, **API unifiée**, **alertes** — d’où le qualificatif *supervised*.

## Couvert (preuve repo)

| Domaine | État | Fichiers / scripts |
|---------|------|-------------------|
| Runners mini-lab | OK | `scripts/run_mini_lab_week.py`, `run_mini_lab_multiweek.py` |
| Nomenclature runs | OK | `run_id`, `output-parent`, `mini_lab_summary_*.json` |
| Manifest campagne | **OK** | `run_manifest.json` (schéma `CampaignManifestV0`) |
| Contrat summary | **OK** | champs `RunSummaryV0` + validation Pydantic |
| Artefacts | OK | `results/labs/mini_week/...`, parquets trades, debug_counts |
| Agrégats playbook | OK | `aggregate_mini_lab_summaries.py`, `aggregate_nf_1r_confirmation.py` |
| Garde-fous risk | OK | `risk_engine.py`, env `RISK_EVAL_*` (mini-lab) |
| Journal trades (export) | Partiel | Parquet trades par run ; `TradeJournal` global souvent neutralisé en lab (`_save` noop) |
| Reprise / redémarrage session | **Manquant** | Pas de service long-running stateful documenté |
| Monitoring / alertes | **Manquant** | Pas de hook standardisé hors logs |

## Checklist paper supervisé

- [x] Lancer un run reproductible avec mêmes flags risk.
- [x] Séparer campagnes (`output-parent`) sans écraser baseline.
- [x] Lire funnel NY/NF/LSS depuis `mini_lab_summary`.
- [x] Agréger NF via `aggregate_nf_1r_confirmation.py` (rollups + gate).
- [x] **`run_manifest.json`** par run mini-lab.
- [x] Validation **Pydantic** `RunSummaryV0` / `CampaignManifestV0` (tests sur artefacts réels).
- [ ] Reprise après crash : **à concevoir** (checkpoint run_id, idempotence).
- [ ] Endpoint HTTP unique « état paper » : **hors scope actuel** (front plus tard).

## Patchs backend faible rayon (recommandés plus tard)

- Option : activer écriture journal parquet contrôlée en lab (flag) pour aligner avec futur contrat front.
- [x] Validateur **TradeRowV0** sur une ligne parquet (`contracts/trade_row_v0.py`, test sur échantillon versionné).

## Rollback

Retirer l’écriture `run_manifest.json` et les champs `contract_version` / `run_started_at_utc` dans `run_mini_lab_week.py` ; les anciens JSON restent valides côté validateur (champs optionnels).
