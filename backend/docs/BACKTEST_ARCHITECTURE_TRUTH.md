# Backtest Architecture Truth (Dexterio) — Socle Exécutable

Objectif de ce document : figer une **source de vérité d’architecture** (repo-driven) pour éviter que Dexterio dérive vers plusieurs “moteurs” concurrents au moment où on branchera un cockpit UI.

Contraintes de cette vérité :

- Pas une doc “marketing” : uniquement ce qui est **prouvé par le code**.
- Pas de conclusion SAFE/paper/live ici (hors scope).
- Le **ladder** (campagnes comparables) est la référence de “run backtest” aujourd’hui.

---

## 1) Définitions (pour éviter les ambiguïtés)

- **Backtest (campagnes/lab)** : replay historique minute par minute (driver 1m), output versionné sous `backend/results/…`, utilisé par le ladder.
- **UI backtests** : backtests déclenchés par API (`/api/backtests/*`), exécutés via jobs.
- **Trading API / paper** : orchestration “live-style” via `TradingPipeline` (pas le moteur backtest).

---

## 2) Moteur canonique (campagnes/lab)

### Moteur

- Canonique : `backend/backtest/engine.py` → `class BacktestEngine`
- Contrat config/résultat : `backend/models/backtest.py` → `BacktestConfig`, `BacktestResult`

### Composants réellement utilisés par BacktestEngine

Dans `BacktestEngine.__init__` (preuve directe via imports/instanciations) :

- `engines/setup_engine_v2.py` → `SetupEngineV2` (**setup engine canonique côté backtest**)
- `engines/timeframe_aggregator.py` → `TimeframeAggregator` (agrégation HTF incrémentale)
- `engines/risk_engine.py` → `RiskEngine` (policy allow/deny + caps + kill-switch)
- `engines/execution/paper_trading.py` → `ExecutionEngine` (même noyau d’exécution que paper)

### Chemin legacy explicitement “dangereux”

`backend/backtest/engine.py` contient encore `_build_multi_timeframe_candles()` (pandas resample) mais le fichier indique explicitement :

- “PERF: **Ne JAMAIS appeler** `_build_multi_timeframe_candles` (legacy path bloquant)”
- `run()` utilise `TimeframeAggregator` + `_process_bar_optimized`, et l’appel legacy est commenté.

Conclusion : **BacktestEngine est la source de vérité** pour le backtest campagnes/lab, et l’agrégation HTF incrémentale est le chemin supporté.

---

## 3) Flux canonique “ladder” (campagnes comparables)

### Runner canonique (1 fenêtre courte)

`backend/scripts/run_mini_lab_week.py` :

- construit `BacktestConfig`
- exécute `BacktestEngine.load_data()` puis `BacktestEngine.run()`
- écrit les artefacts “ladder” sous :
  - `backend/results/labs/mini_week/<output_parent>/<label>/`

Artefacts canoniques (contrat utilisé par audit/rollup) :

- `run_manifest.json` (couverture data + env snapshot + git_sha + argv + cwd)
- `mini_lab_summary_*.json` (résumé + `trade_metrics_parquet` si parquet présent)
- `trades_*.parquet`, `equity_*.parquet`, `summary_*.json`, `debug_counts_*.json`, etc.

### Walk-forward canonique (2 splits)

`backend/scripts/run_walk_forward_mini_lab.py` :

- **n’instancie pas de moteur**
- enchaîne des sous-processus `run_mini_lab_week.py`
- écrit `walk_forward_campaign.json` dans le dossier `output_parent`

### Post-run canonique

- `backend/scripts/audit_campaign_output_parent.py` (audit nested/flat, lit les `mini_lab_summary` + `walk_forward_campaign.json` si présent)
- `backend/scripts/rollup_campaign_summaries.py` (agrège en `CampaignRollupV0`)

**Règle** : une campagne FULL comparable = (runner ladder) + (manifest) + (summary) + (audit) + (rollup) + `git_sha` cohérent.

---

## 4) UI / API : ce qui existe, et ce qui est “autorisé” pour le cockpit

### Serveur principal (supporté)

- `backend/server.py` : FastAPI principal (inclut `routes/trading` et `routes/backtests`)
- `backend/routes/backtests.py` : endpoints UI backtests, délègue à `jobs/backtest_jobs.py`
- `backend/jobs/backtest_jobs.py` : worker jobs qui exécute `BacktestEngine` (ProcessPoolExecutor)

**Point clé** : aujourd’hui, l’API backtests utilise le **même moteur** (`BacktestEngine`) que les campagnes/lab.

### Serveur alternatif (ambigu / legacy)

- `backend/server_extended.py` : deuxième app FastAPI qui instancie `DataFeedEngine`, `MarketStateEngine`, `LiquidityEngine` et expose des endpoints.

Risque : deux apps “exécutables” → **UI fragile** si elle branche “le mauvais serveur” (comportements/configs différents).

### Trading API / paper (secondaire, pas canonique backtest)

- `backend/routes/trading.py` → `TradingPipeline` (`backend/engines/pipeline.py`)

Différences structurelles majeures vs BacktestEngine :

- `TradingPipeline` utilise `engines/setup_engine.py` (`SetupEngine` legacy), pas `SetupEngineV2`.
- Le flux est “analyse live-style” (data_feed multi-TF, scoring, filtering), pas un replay historique unifié par minute.

Conclusion : **le cockpit UI backtest** doit piloter le chemin **BacktestEngine**, pas `TradingPipeline`.

---

## 5) Carte des entrypoints (canonique / supporté / secondaire / legacy / dangereux)

Canonique (campagnes/lab + ladder) :

- `backend/backtest/engine.py` (`BacktestEngine`)
- `backend/models/backtest.py` (`BacktestConfig`, `BacktestResult`)
- `backend/scripts/run_mini_lab_week.py`
- `backend/scripts/run_walk_forward_mini_lab.py`
- `backend/scripts/audit_campaign_output_parent.py`
- `backend/scripts/rollup_campaign_summaries.py`

Supporté (UI backtests, même moteur, **artefacts ladder-minimaux écrits** dans `results/jobs/<job_id>/`) :

- `backend/server.py`
- `backend/routes/backtests.py`
- `backend/jobs/backtest_jobs.py`

Secondaire (outil / CLI, utile mais pas le protocole ladder) :

- `backend/backtest/run.py` (CLI direct BacktestEngine)
- divers scripts/tools qui instancient `BacktestEngine` pour debug/profiling

Legacy / ambigu :

- `backend/server_extended.py` (app alternative)
- `backend/engines/pipeline.py` (trading pipeline)
- `backend/engines/setup_engine.py` (setup engine legacy)

Dangereux si réactivé / modifié sans garde :

- `backend/backtest/engine.py::_build_multi_timeframe_candles()` (path perf legacy “bloquant”)
- `backend/engines/playbook_loader.py.backup` (fichier shadow, risque humain)

---

## 6) Réponse UI centrale : quel chemin doit piloter le backtest ?

Si demain on construit le cockpit UI Dexterio et qu’on veut rester **strictement compatible** avec le ladder et les campagnes FULL :

- UI doit appeler `backend/server.py` (FastAPI) → `routes/backtests.py` → `jobs/backtest_jobs.py` → `BacktestEngine`.
- UI ne doit **pas** piloter `server_extended.py` pour le backtest.
- UI ne doit **pas** interpréter `TradingPipeline` comme moteur de backtest (c’est un pipeline “live-style”).

Condition d’unification cockpit (désormais **partiellement satisfaite**) :

- Les jobs UI doivent produire des artefacts **compatibles ladder** (`run_manifest.json` + `mini_lab_summary_*.json`) dans leur dossier `results/jobs/<job_id>/`.
- Ce contrat minimal rend les jobs **auditables/rollupables** via les scripts ladder avec `--path` (layout `flat`), mais ne remplace pas le protocole `mini_week` (layout/flags).

---

## 7) Divergences structurelles prouvées (à surveiller)

- Artefacts:
  - ladder écrit `run_manifest.json` + `mini_lab_summary_*.json` sous `results/labs/mini_week/...`
  - jobs UI écrivent désormais aussi `run_manifest.json` + `mini_lab_summary_*.json` sous `results/jobs/<job_id>/` (layout “jobs”, pas “mini_week”)
- Env flags / policy risk:
  - `run_mini_lab_week.py` force des flags (`RISK_EVAL_RELAX_CAPS`, `RISK_EVAL_DISABLE_KILL_SWITCH`, …) qui ne sont pas explicitement forcés par `jobs/backtest_jobs.py`
- Setup engine:
  - BacktestEngine = `SetupEngineV2`
  - TradingPipeline = `SetupEngine` legacy
- Serveur:
  - deux apps FastAPI (`server.py` vs `server_extended.py`)

---

## 8) Statut (unification UI backtests → ladder)

✅ Réalisé : les **UI backtests jobs** écrivent désormais un contrat ladder-minimal (sans changer le trading) :

- `results/jobs/<job_id>/run_manifest.json` (`CampaignManifestV0`)
- `results/jobs/<job_id>/mini_lab_summary_*.json` (compatible `RunSummaryV0` pour audit/rollup)

Limites restantes (volontairement non traitées ici) :

- Le layout “jobs” reste distinct du layout `results/labs/mini_week/...` (ce n’est pas un `output_parent` mini_week).
- `run_mini_lab_week.py` force des env flags risk (ex: relax caps / disable kill-switch) alors que les jobs UI ne les forcent pas : comparabilité = OK sur le moteur, mais pas nécessairement sur la **policy**.
