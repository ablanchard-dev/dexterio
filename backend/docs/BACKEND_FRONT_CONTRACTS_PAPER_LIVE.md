# Contrats de données backend → futur front paper / live

**Statut** : spécification **sans UI** ; implémentation front **plus tard**.

## 1. Objets nécessaires au front

| Concept | Usage front | Existant aujourd’hui | Lacunes |
|---------|-------------|---------------------|---------|
| Run summary | Carte « dernier run » | `mini_lab_summary_*.json` | Pas de schéma versionné unique |
| Playbook funnel | Tableau M/S/SR/T | `funnel` dans summary + `debug_counts` | Champs dispersés |
| Trade journal | Liste trades, filtres | `trades_*_AGGRESSIVE_DAILY_SCALP.parquet` | Pas d’API ; colonnes stables mais non versionnées |
| Active positions | Paper live | `ExecutionEngine` / pipeline | Pas sérialisé pour HTTP |
| Risk stats | Drawdown, caps | `risk_engine_stats_*.json` | Par run, pas agrégé multi-run |
| Setup candidates | Debug A+ | `grading_debug_*.json`, jsonl scoring | Volume élevé ; pas de contrat stable |
| Session paper | Reprise | — | **Non défini** |

## 2. Contrat stable proposé (v0)

### 2.1 `RunSummaryV0` (JSON)

Champs **minimum** alignés sur `mini_lab_summary` actuel :

- `protocol`, `runner`, `git_sha`, `run_id`, `start_date`, `end_date`, `symbols[]`
- `total_trades`, `final_capital` (string)
- `funnel`: map `playbook_name → { matches, setups_created, after_risk, trades }`
- `respect_allowlists`, `bypass_lss_quarantine`, `output_parent?`, `playbooks_yaml?`

### 2.2 `TradeRowV0` (parquet / CSV)

Aligné sur colonnes actuelles du export backtest :

- `trade_id`, `timestamp_entry`, `timestamp_exit`, `symbol`, `playbook`, `direction`, `trade_type`
- `entry_price`, `exit_price`, `stop_loss`, `take_profit_1`, `r_multiple`, `outcome`, `exit_reason`, `duration_minutes`

### 2.3 `CampaignManifestV0` (futur, optionnel)

- `campaign_id`, `started_at`, `command_argv`, `git_sha`, `preset`, `output_parent`

## 3. Implémentation backend (cette livraison)

**Aucun code nouveau** : ce document **fige les noms** pour éviter dérive lors du front. Les fichiers existants **sont** la référence jusqu’à introduction d’un validateur (Pydantic / JSON Schema) en phase ultérieure.

## 4. Incohérences connues

- `final_capital` en string dans summary (legacy).
- Plusieurs formats de nom de fichier trades selon `run_id`.

## NEXT

- Ajouter `schemas/run_summary_v0.json` + test de validation sur un `mini_lab_summary` réel (patch futur faible risque).
