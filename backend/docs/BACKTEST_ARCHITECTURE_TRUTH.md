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

### Layout canonique `results/labs/mini_week/` (nested vs flat)

Les outils campagne (`audit/rollup`) supportent **2 dispositions** (détection auto par présence de `mini_lab_summary*.json`) :

- **nested (campagnes / output_parent)** : `results/labs/mini_week/<output_parent>/<label>/`
  - **strictement requis** : `mini_lab_summary*.json` dans chaque dossier `<label>/` (sinon le run n’est pas détecté)
  - **optionnel mais recommandé** : `run_manifest.json` dans chaque dossier `<label>/`
  - **walk-forward** (optionnel) : `results/labs/mini_week/<output_parent>/walk_forward_campaign.json`
- **flat (run seul / baseline historique)** : `results/labs/mini_week/<label>/`
  - **strictement requis** : `mini_lab_summary*.json` directement dans le dossier `<label>/`

Conclusion : pour qu’un run UI soit traité comme un run campagne “normal” par les outils ladder,
il doit écrire au minimum un `mini_lab_summary*.json` dans un dossier compatible nested/flat.

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

### Protocoles UI backtests (jobs)

Les jobs UI exposent désormais un champ explicite `protocol` (dans `BacktestJobRequest`) :

- `protocol="JOB"` (défaut) :
  - policy/env “brute” (ne force pas `RISK_EVAL_RELAX_CAPS` / `RISK_EVAL_DISABLE_KILL_SWITCH`)
  - conserve `htf_warmup_days` tel que demandé dans la requête
- `protocol="MINI_LAB_WEEK"` :
  - aligne le protocole sur `scripts/run_mini_lab_week.py` (flags risk structurants)
  - force `htf_warmup_days=30` (écrit dans `protocol_overrides`)
  - évite de muter le `trade_journal` global (journal local au job, save désactivé)
- `protocol="MINI_LAB_WALK_FORWARD"` :
  - lance une **mini-campagne walk-forward 2 splits OOS** (labels auto-générés `wf_s0_test`, `wf_s1_test` par défaut)
  - réutilise l’orchestrateur canonique `scripts/run_walk_forward_mini_lab.py` (qui spawn `scripts/run_mini_lab_week.py` par fenêtre)
  - écrit directement sous le layout canonique :
    - `results/labs/mini_week/<output_parent>/wf_s0_test/…`
    - `results/labs/mini_week/<output_parent>/wf_s1_test/…`
    - `results/labs/mini_week/<output_parent>/walk_forward_campaign.json`

Traçabilité : `protocol` est écrit dans `run_manifest.json` et dans `mini_lab_summary_*.json`.

### Lecture des résultats (cockpit-friendly)

Endpoints (preuve : `backend/routes/backtests.py`) :

- `GET /api/backtests/{job_id}` : statut du job (lit `results/jobs/<job_id>/job.json`)
- `GET /api/backtests/{job_id}/results` : retourne `metrics`, `artifact_paths`, `download_urls`
  - et **si** `results/jobs/<job_id>/campaign_pointer.json` existe : expose aussi un bloc `campaign`
    (lit/parsing `campaign_pointer.json`) qui fournit directement :
    - `campaign_root` (racine canonique)
    - `walk_forward_campaign_path`, `campaign_audit_path`, `campaign_rollup_path` (chemins canoniques)
    - `job_files` + `job_download_urls` (artefacts job-facing téléchargeables)

### Serveur alternatif (ambigu / legacy)

- `backend/server_extended.py` : deuxième app FastAPI qui instancie `DataFeedEngine`, `MarketStateEngine`, `LiquidityEngine` et expose des endpoints.

Risque : deux apps “exécutables” → **UI fragile** si elle branche “le mauvais serveur” (comportements/configs différents).

### Trading API / paper (secondaire, pas canonique backtest)

- `backend/routes/trading.py` → `TradingPipeline` (`backend/engines/pipeline.py`)

Différences structurelles majeures vs BacktestEngine :

- `TradingPipeline` utilise `engines/setup_engine.py` (`SetupEngine` legacy), pas `SetupEngineV2`.
- Le flux est “analyse live-style” (data_feed multi-TF, scoring, filtering), pas un replay historique unifié par minute.
- `SetupEngine.score_setup()` ne peuple jamais `setup.playbook_name` (toujours `''`).
- `PlaybookEngine` (4 classes Python hardcodées) utilise des noms différents des playbooks YAML :
  `NY_Open_Reversal`, `London_Sweep`, `Trend_Continuation_Pullback`, `ICT_Manipulation_Reversal`.
  Seul `NY_Open_Reversal` est dans `AGGRESSIVE_ALLOWLIST`. Les trois autres sont bloqués par la policy.

**Guard canonique ajouté (2026-04-16) :**
- `TradingPipeline.run_full_analysis()` applique désormais un guard ALLOWLIST/DENYLIST au step 8b.
- Implémenté via `self.risk_engine.is_playbook_allowed(m.playbook_name)` sur chaque `playbook_matches`.
- Miroir exact du check dans `evaluate_multi_asset_trade()` (risk_engine.py lignes 864-868).
- Résultat : `London_Sweep`, `Trend_Continuation_Pullback`, `ICT_Manipulation_Reversal` sont bloqués en AGGRESSIVE.
  `NY_Open_Reversal` passe. Setups sans playbook_matches passent (pas de contrainte policy sans match).
- Tests : `backend/tests/test_pipeline_canonical_guard.py` — 11 cas, 11 passés.

**Fix D1+D2 (2026-04-16) — commit `b56b982` :**
- `calculate_playbook_score()` utilisait `p.match_score` (inexistant sur `PlaybookMatch`) → crash.
  Corrigé : utilise `p.confidence` (champ réel du modèle).
- `_determine_direction()` Priorité 1 utilisait `p.match_score` et `p.direction` (tous deux inexistants).
  Corrigé : branche supprimée. Direction vient du BOS ICT (Prio 2) puis candlestick (Prio 3).
- Avant ce fix : `SetupEngine` produisait 0 setup pour 75% des scénarios (playbook_matches non vide).
- Après : peut produire des setups, divergences D3-D7 deviennent mesurables sur vrais artefacts shadow.
- Tests : `backend/tests/test_setup_engine_direction.py` — 14 cas, 14 passés.

**Ce qui reste divergent :**
- Scoring : `SetupEngine` (poids fixes, `confidence`) ≠ `SetupEngineV2` (YAML, named components, grade_thresholds).
- HTF aggregation : `DataFeedEngine.aggregate_to_higher_tf` (pandas batch) ≠ `TimeframeAggregator` (incrémental).
- `setup.playbook_name` toujours `''` côté legacy (non corrigé, non bloquant pour le guard).
- V2 over-génère (10 raw setups invariants par input, `Liquidity_Sweep_Scalp` dominant) — mesurable maintenant.

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

- Les jobs UI produisent des artefacts **compatibles ladder** (`run_manifest.json` + `mini_lab_summary_*.json`) dans `results/jobs/<job_id>/`.
- Si `protocol="MINI_LAB_WEEK"` et `output_parent+label` sont fournis, le job écrit aussi ces artefacts dans le **layout canonique** `results/labs/mini_week/<output_parent>/<label>/` (nested), ce qui permet `audit/rollup` via `--output-parent` (sans contournement `--path results/jobs/...`).
- Si `protocol="MINI_LAB_WALK_FORWARD"` et `output_parent` est fourni, le job déclenche une **mini-campagne walk-forward canonique** (2 splits OOS) sous `results/labs/mini_week/<output_parent>/` :
  - labels `wf_s0_test`, `wf_s1_test` (par défaut)
  - `walk_forward_campaign.json`
  - **cockpit-ready** : `campaign_audit.json` + `campaign_rollup.json` (post-traitement auto du worker via les scripts `audit_campaign_output_parent.py` et `rollup_campaign_summaries.py`)
  - consommable par `audit/rollup` via `--output-parent` (sans `--path results/jobs/...`).

---

## 7) Divergences structurelles prouvées (à surveiller)

- KPI / métriques (vérité unique cockpit/ladder) :
  - Définitions verrouillées : `backend/backtest/metrics.py` (PF en **R**, expectancy = **mean(r_multiple)** incluant BE).
  - Le moteur (`BacktestEngine`) expose désormais `BacktestResult.expectancy_r` et `BacktestResult.profit_factor`
    selon ces définitions (pas une formule win/loss, pas un PF en $).
  - **MaxDD canonique** : `max_drawdown_r` = max drawdown sur la cumulative `pnl_R_account`
    (net `$` / `base_r_unit_$`), cohérent avec `RiskEngine.state.max_drawdown_r` et avec
    `max_drawdown_dollars / base_r_unit_$`.
    - Le moteur (`BacktestEngine`) expose `BacktestResult.max_drawdown_r` selon cette définition.
    - Le ladder expose `mini_lab_summary.trade_metrics_parquet.max_drawdown_r` (depuis `trades.parquet`).
    - Le rollup expose `CampaignRollupV0.max_drawdown_r_max` (= max des MaxDD par run ; l’agrégat exact d’une campagne requiert l’union des parquets trades).
  - Les métriques ladder dérivées du parquet trades (`mini_lab_summary.trade_metrics_parquet`) suivent les mêmes
    définitions, et le rollup campagne agrège PF via Σ gross_profit_r / |Σ gross_loss_r| quand disponible.

- Artefacts:
  - ladder écrit `run_manifest.json` + `mini_lab_summary_*.json` sous `results/labs/mini_week/...`
  - jobs UI écrivent aussi `run_manifest.json` + `mini_lab_summary_*.json` sous `results/jobs/<job_id>/` (layout “jobs”)
  - en `protocol="MINI_LAB_WEEK"` + `output_parent+label`, les jobs UI écrivent **en plus** dans `results/labs/mini_week/<output_parent>/<label>/` (bridge canonique) :
    - `run_manifest.json` + `mini_lab_summary_*.json` (contrat ladder)
    - et les artefacts moteur (`summary_*.json`, `trades_*.parquet`, `equity_*.parquet`, `debug_counts_*.json`, …) car `BacktestConfig.output_dir` pointe vers ce dossier canonique
  - en `protocol="MINI_LAB_WALK_FORWARD"` + `output_parent`, les runs sont produits sous `results/labs/mini_week/<output_parent>/<wf_label>/` via `scripts/run_walk_forward_mini_lab.py` → `scripts/run_mini_lab_week.py` (subprocess).
    - Canonique : `walk_forward_campaign.json` + `campaign_audit.json` + `campaign_rollup.json` sont écrits sous la racine campagne `results/labs/mini_week/<output_parent>/`.
    - Job-facing (porte d’entrée cockpit) : le job copie aussi ces JSON dans `results/jobs/<job_id>/` (sans dupliquer les sous-dossiers de runs) et expose les fichiers via `artifact_paths` + `campaign_pointer.json`.
- Env flags / policy risk:
  - `run_mini_lab_week.py` force des flags (`RISK_EVAL_RELAX_CAPS`, `RISK_EVAL_DISABLE_KILL_SWITCH`, …).
  - `jobs/backtest_jobs.py` :
    - en `protocol="JOB"` : ne force pas ces flags (policy brute)
    - en `protocol="MINI_LAB_WEEK"` : force ces flags (alignement mini-lab)
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
- Et (optionnel) si `protocol="MINI_LAB_WEEK"` + `output_parent+label` :
  - `results/labs/mini_week/<output_parent>/<label>/run_manifest.json`
  - `results/labs/mini_week/<output_parent>/<label>/mini_lab_summary_*.json`
- Et (optionnel) si `protocol="MINI_LAB_WALK_FORWARD"` + `output_parent` :
  - `results/labs/mini_week/<output_parent>/wf_s0_test/…`
  - `results/labs/mini_week/<output_parent>/wf_s1_test/…`
  - `results/labs/mini_week/<output_parent>/walk_forward_campaign.json`
  - `results/labs/mini_week/<output_parent>/campaign_audit.json`
  - `results/labs/mini_week/<output_parent>/campaign_rollup.json`
  - et côté job (porte d’entrée cockpit) :
    - `results/jobs/<job_id>/campaign_pointer.json`
    - `results/jobs/<job_id>/walk_forward_campaign.json`
    - `results/jobs/<job_id>/campaign_audit.json`
    - `results/jobs/<job_id>/campaign_rollup.json`

Limites restantes (volontairement non traitées ici) :

- `protocol="JOB"` reste **dans** `results/jobs/<job_id>/` (pas un `output_parent` mini_week).
- `protocol="MINI_LAB_WEEK"` peut rejoindre le layout canonique, mais le job n’est pas un clone parfait de `scripts/run_mini_lab_week.py` :
  - pas d’override `--playbooks-yaml` côté jobs UI (à ce stade)
  - runner différent (traçabilité OK via `runner=jobs/backtest_jobs.py`)
- `protocol="MINI_LAB_WALK_FORWARD"` réutilise l’orchestrateur canonique `scripts/run_walk_forward_mini_lab.py`, mais ce protocole UI n’expose pas encore toutes les options CLI (ex. `--plan`, `--include-train`, forwarded argv arbitrés) — volontairement minimal.
- La comparabilité “policy” dépend du protocole :
  - `JOB` ≠ mini-lab (volontaire)
  - `MINI_LAB_WEEK` vise l’alignement mini-lab
