# Contrats de données backend → futur front paper / live

**Statut** : spécification **sans UI** ; **validation Pydantic** en place pour deux contrats.

## 1. Objets nécessaires au front

| Concept | Usage front | Existant aujourd’hui | Validation |
|---------|-------------|---------------------|------------|
| Run summary | Carte « dernier run » | `mini_lab_summary_*.json` | **`contracts/run_summary_v0.py`** (`RunSummaryV0`) |
| Campaign manifest | Traçabilité / reprise future | **`run_manifest.json`** | **`contracts/campaign_manifest_v0.py`** (`CampaignManifestV0`) |
| Playbook funnel | Tableau M/S/SR/T | `funnel` dans summary | Via `RunSummaryV0.funnel` |
| Trade journal | Liste trades | `trades_*_AGGRESSIVE_DAILY_SCALP.parquet` | **`contracts/trade_row_v0.py`** (`TradeRowV0`) |
| Active positions | Paper live | `ExecutionEngine` | Non sérialisé |
| Risk stats | Drawdown, caps | `risk_engine_stats_*.json` | Non versionné |

## 2. Contrats implémentés (code)

### 2.1 `RunSummaryV0`

- Module : `backend/contracts/run_summary_v0.py`
- Test : `tests/test_run_summary_v0_contract.py` (artefact `mini_week/202511_w01/mini_lab_summary_*.json` + cas synthétique).
- Champs **obligatoires** : `protocol`, `runner`, `git_sha`, `run_id`, dates, `symbols`, flags risk, `total_trades`, `final_capital`, `funnel` (5 playbooks mini-lab standard).
- Champs **optionnels** : `output_parent`, `playbooks_yaml`, `nf_tp1_rr_meta`, `contract_version`, `run_started_at_utc` (émis par les **nouveaux** runs).

### 2.2 `CampaignManifestV0`

- Module : `backend/contracts/campaign_manifest_v0.py`
- Test : `tests/test_campaign_manifest_v0_contract.py` (artefact `wave2_fvg_w21_validate/202509_w01/run_manifest.json`).
- Champs **optionnels** (nouveaux runs mini-lab) : `run_clock_mode` (`BACKTEST` pour l’instant), `lab_environment` (snapshot `RISK_*` via `utils/lab_environment_snapshot.py`, inspiration reproductibilité type Freqtrade dry-run / config figée).

### 2.3 `TradeRowV0`

- Module : `backend/contracts/trade_row_v0.py`
- Test : `tests/test_trade_row_v0_contract.py` (échantillon `data/backtest_results/trades_costs_test_1d_AGGRESSIVE_DAILY.parquet` + cas synthétique).
- Colonnes **obligatoires** (colonnes parquet additionnelles ignorées) :  
`trade_id`, `timestamp_entry`, `timestamp_exit`, `symbol`, `playbook`, `direction`, `trade_type`, `entry_price`, `exit_price`, `stop_loss`, `take_profit_1`, `r_multiple`, `outcome`, `exit_reason`, `duration_minutes`.

## 3. Incohérences connues

- `final_capital` en string dans summary (legacy).
- Noms de fichiers trades dépendent de `run_id`.

## NEXT

- Option : étendre `TradeRowV0` avec champs optionnels (`quality`, `pnl_dollars`, …) si le front en a besoin.
