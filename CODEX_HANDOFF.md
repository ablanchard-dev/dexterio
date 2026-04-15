# CODEX_HANDOFF.md
# DexterioBOT — Handoff pour Codex / nouvelle session
# Dernière mise à jour : 2026-04-15

---

## 1. État exact du repo

- Branche : `main`
- HEAD actuel (source de vérité) : exécuter `git rev-parse --short HEAD`
- UI jobs → artefacts ladder-min (manifest + mini_lab_summary) : commit `7da796e`
- UI jobs → protocoles explicites (`JOB` vs `MINI_LAB_WEEK`) : voir les commits suivants (`git log -5 --oneline`)
- **Statut worktree :** repo historiquement "sale" (beaucoup de fichiers/artefacts hors scope). Ne pas les nettoyer ni les revert sans demande explicite.
- **Cartographie FULL (repo-driven, versionnée) :**
  - JSON canonique : `backend/results/full_portfolio_map/full_portfolio_map.json`
  - Vue lisible : `backend/docs/FULL_PORTFOLIO_MAP.md`
  - Génération : `backend/scripts/generate_full_portfolio_map.py`
- **UI backtests (jobs) désormais ladder-min compatibles :**
  - Code : `backend/jobs/backtest_jobs.py`
  - Protocoles :
    - `protocol=JOB` (défaut) : policy/env brute
    - `protocol=MINI_LAB_WEEK` : aligne flags risk mini-lab + `htf_warmup_days=30` (voir `protocol_overrides` dans le manifest)
  - Artefacts écrits dans `backend/results/jobs/<job_id>/` :
    - `run_manifest.json` (`CampaignManifestV0`)
    - `mini_lab_summary_job_<job_id>.json` (compatible `RunSummaryV0` pour audit/rollup)
  - Validation rapide (sans serveur) :
    - exécuter `run_backtest_worker` localement, puis :
    - `cd backend && .venv/bin/python scripts/audit_campaign_output_parent.py --path results/jobs/<job_id>`
    - `cd backend && .venv/bin/python scripts/rollup_campaign_summaries.py --path results/jobs/<job_id>`
- **Artefacts de validation "postfix" (preuves sur `git_sha=4e7246a`) :**
  - `backend/results/labs/mini_week/ifvg_probe_sep29_oct02_postfix/`
  - `backend/results/labs/mini_week/ifvg_oos_jun_nov2025_postfix/`
- **Artefacts "covfix" (preuves sur `git_sha=c56d26d`) :**
  - `backend/results/labs/mini_week/ifvg_oos_jun_nov2025_postfix_covfix/`
- **Artefacts historiques (pré-fix / hors preuve HEAD courant) :**
  - `backend/results/labs/mini_week/ifvg_probe_sep29_oct02/`
  - `backend/results/labs/mini_week/ifvg_oos_jun_nov2025/`
  - `backend/results/labs/mini_week/smoke_ifvg_5m/`

---

## 2. Ce qui a été fini récemment (passe 2026-04-14)

### P1b — Fix sweep scoring (plomberie)

**Deux bugs code corrigés :**

1. `engines/patterns/custom_detectors.py` : `detect_custom_patterns` n'appelait pas
   `detect_liquidity_sweep` → la clé `"liquidity_sweep"` manquait dans le dict
   `ict_patterns` → `liquidity_sweep_score = 0.0` sur 100% des trades, toujours.

2. `engines/playbook_loader.py` + 3 autres fichiers : `has_sweep` vérifiait
   `== 'sweep'` alors que `ICTPatternEngine` émet `pattern_type='liquidity_sweep'`.

**Autres corrections moteur dans la même passe :**
- `playbook_loader.py` : `is_backtest_aggressive` lisait `settings.TRADING_MODE`
  global (SAFE) au lieu du `trading_mode` du run → propagation du mode du run ajoutée
- `backtest/engine.py` : guard `None` sur `self.config.run_name` (crash si non défini)

**Résultat P1b :** Bug code corrigé. Sur Aug 4-8 SPY, 0 sweeps détectés (fait de
marché, pas un bug). Détecteur vérifié actif : 42 jours avec sweeps sur Aug-Sep 2025.

### P2 — IFVG 5m smoke (pipeline actif)

**3 blocages moteur résolus :**

1. `engines/setup_engine_v2.py` — `_determine_direction` retournait `None` pour
   les playbooks IFVG quand `bias='neutral'` → setups tous droppés. Fix : branch IFVG
   en tête du code, direction déduite du nom (`BULL`→LONG, `BEAR`→SHORT).

2. `engines/playbook_loader.py` — raw IFVG strength ≈ 0.001 (détecteur utilise
   `displacement * 10`, SPY = ~0.001) → `fvg_alignment` et `ifvg_quality` donnaient
   un score ≈ 0.001. Fix : plancher 0.65 si IFVG détecté (présence = signal validé).

3. `knowledge/campaigns/campaign_smoke_ifvg_5m.yml` — `pattern_quality: 0.30`
   toujours nul (IFVG playbooks ont `required_families: []`). Remplacé par
   `ifvg_quality: 0.80`.

**Résultat smoke AGGRESSIVE SCALP SPY Aug 4-8 :**
```
Trades : 10 (5 Bull, 5 Bear) | WR 50% | E[R] -0.069 | PF 0.24
Grades : A 3, B 7 | Exit : time_stop 6, SL 4
```
Pipeline fonctionnel. Pas un edge validé (10 trades = bruit statistique pur).

### P3 — Blocage moteur / perf IFVG 5m jun-nov 2025

**Symptôme reproduit :**
- Freeze reproductible autour de `BAR 33800`
- Timestamp observé : `2025-09-30 12:01:00+00:00`
- Process vivant, CPU ~100%, log immobile pendant ~35 min
- Le walk-forward a été tué car le moteur semblait bloqué dans une boucle coûteuse ou quasi-infinie
- Le blocage apparaissait même sur des runs resserrés et en `SPY` only

**Cause racine :**
- Dans `backend/backtest/engine.py`, `_process_bar_optimized` recalculait le master candle 1m en rescannant l'historique complet des `candles_1m` à chaque barre / setup.
- Comme la série s'allonge à chaque itération, le coût devenait quadratique (`O(n²)`), avec un effet apparent de blocage sur la fenêtre longue.
- Correction appliquée : `_ingest_master_candle_1m` alimente un cache sessionnel en `O(1)` et `_get_master_candle_cached` calcule le master candle uniquement à partir du buffer de session courant.

**Patch appliqué (commité) :**
- Commit `4e7246a` sur `main`
- Fichier principal : `backend/backtest/engine.py` (cache Master Candle 1m)

**Validation ciblée post-fix (preuves `git_sha=4e7246a`) :**
- Repro minimale SPY-only terminée : `ifvg_probe_sep29_oct02_postfix/ifvg_sep29_oct02_postfix` (`total_trades=6`, `data_coverage_ok=true`)
- Campagne OOS IFVG 5m relancée et terminée (2 splits) : `ifvg_oos_jun_nov2025_postfix/{wf_s0_test,wf_s1_test}`
- Preuve d'absence de freeze : le run `wf_s0_test` passe par `BAR 33800` à `2025-09-30 12:01:00+00:00` sans blocage
- Audit/rollup : `overall_ok=false` (car `wf_s1_test` a `data_coverage_ok=false`), `total_trades_sum=352`, `expectancy_r_weighted_by_trades=-0.04822238609801143`
- Limite restante : `wf_s1_test` couverture data incomplète, à traiter comme **limite data** (pas bug moteur)

### P4 — Contrat `data_coverage_ok` (date-only `--end`, faux négatif RTH/UTC)

**Symptôme :**
- `backend/results/labs/mini_week/ifvg_oos_jun_nov2025_postfix/wf_s1_test/run_manifest.json` :
  `data_coverage.coverage_ok=false` avec erreurs du type :
  `max datetime 2025-11-28 21:59:00+00:00 < fin de fenêtre attendue (2025-11-29 00:00:00+00:00 exclus)`.
- Ça bloquait `audit_campaign_output_parent` / `rollup` via le gate "coverage", alors que les données contiennent bien la journée `2025-11-28`.

**Cause racine (bug de contrat de coverage, pas trading) :**
- `backend/utils/backtest_data_coverage.py` exigeait implicitement une barre proche de `23:59 UTC` sur `end_date`
  (comparaison sur `end_exclusive_utc`), ce qui produit un faux négatif sur des datasets equities RTH-only
  (pas de barres overnight jusqu'à 23:59 UTC).

**Patch minimal :**
- Si `end_date` est fourni en format `YYYY-MM-DD` (date-only), la couverture exige désormais seulement
  que `tmax` soit sur le **jour** `end_date` (i.e. `tmax.date() >= end_date`), au lieu d'exiger `tmax >= end_exclusive_utc - 1s`.
- Fichiers :
  - `backend/utils/backtest_data_coverage.py`
  - `backend/tests/test_backtest_data_coverage.py` (test RTH)

**Preuves post-patch (HEAD=4e7246a, logique revalidée) :**
- `scripts/backtest_data_preflight.py --start 2025-10-14 --end 2025-11-28 --symbols SPY,QQQ --ignore-warmup-check` → `ok=True`
- Artefact probe :
  - `backend/results/labs/mini_week/data_coverage_contract_probe/coverage_enddate_probe/run_manifest.json`
  - `data_coverage.coverage_ok=true` avec `max_utc=2025-11-28T21:59:00+00:00` et `end_exclusive_utc=2025-11-29T00:00:00+00:00`

### P5 — Régénération campagne OOS IFVG "postfix covfix" (artefacts cohérents sur HEAD courant)

**Objectif :** obtenir des artefacts OOS IFVG postfix auditablement cohérents sur le HEAD courant,
sans faux négatif `data_coverage_ok`.

**Runs relancés (campagne 2 splits homogène) :**
- `backend/results/labs/mini_week/ifvg_oos_jun_nov2025_postfix_covfix/wf_s0_test/`
- `backend/results/labs/mini_week/ifvg_oos_jun_nov2025_postfix_covfix/wf_s1_test/`
  - `git_sha=ad8ba70...` sur les deux splits
  - `data_coverage.coverage_ok=true` (inclut fin RTH-only `max_utc=2025-11-28T21:59:00+00:00`)

**Audit/Rollup :**
- `scripts/audit_campaign_output_parent.py --output-parent ifvg_oos_jun_nov2025_postfix_covfix` → `overall_ok=true`
- `scripts/rollup_campaign_summaries.py --path results/labs/mini_week/ifvg_oos_jun_nov2025_postfix_covfix`
  - `total_trades_sum=352`
  - `expectancy_r_weighted_by_trades=-0.04822238609801143` (2 runs)

---

## 3. Derniers commits importants

```
c3eb1d6  P1 diagnostic complet — liquidity_sweep_score=0 toujours, P2 IFVG 5m actif
cf04d4b  P1 verdict NOT_READY — NY fréquence aberrante (44 trades/j), P1b NY capped actif
5b40ab1  P0 clos — gate REOPEN_1R_VS_1P5R UNRESOLVED
84d6af9  chore(sync): checkpoint all local workspace changes before push
d5e4b24  chore(campaigns): WF core3 NY-only + compares vs baseline and no-FVG
9716e2d  chore(campaigns): WF core3 FVG-only + truth table; proof artifacts
b8ac81f  chore(campaigns): WF core3 NY+Session without FVG + proof artifacts
99a5780  chore(results): WF core3 stricter_grades run + rollup audit postmortem compare
```

**Note :** les passes P1b/P2/P3/P4/P5 ont été intégrées et commitées sur `main` (voir `git log`).

---

## 4. Vérité du projet Dexterio aujourd'hui

Direction unique :
```
backtest crédible → campagnes comparables → portefeuille discipliné → paper limité honnête
```

Toutes les campagnes core-3 OOS (jun–nov 2025, SPY+QQQ) sont **négatives** :
- Trio NY+FVG+Session : E[R] de -0.027 à -0.039 selon variante
- Stricter grades : quasi aucun delta vs baseline
- No-FVG : moins de trades, pas meilleur globalement
- FVG-only : pire
- NY-only : intéressant sur un split (oct/nov E[R]≈-0.001) mais non validé globalement

**Aucun playbook n'a prouvé un edge positif sur l'enveloppe complète.**

---

## 5. Vérité sur le MASTER et les timeframes

- MASTER = 71 transcripts YouTube ICT/smart money dans `/home/dexter/Documents/MASTER_FINAL.txt`
- Framework réel du MASTER : **biais D/4H → setup 15m/5m → entrée/confirmation 1m**
- Les playbooks actuels compriment des concepts 5m en 1m → bruit et fréquence excessive
- Le 1m n'est **pas** le timeframe conceptuel principal sauf cas très spécifiques (News_Fade)
- IFVG 5m = application directe du MASTER (Aplus_01/03) → plus aligné conceptuellement
- HTF + 15m BOS (Aplus_04) = autre application directe non encore testée

---

## 6. Vérité sur le portefeuille playbooks

Source de vérité exécution : `backend/engines/risk_engine.py` (ALLOWLIST / DENYLIST)

| Playbook | Statut code | Verdict campagne |
|----------|-------------|-----------------|
| `NY_Open_Reversal` | ALLOWLIST | NOT_READY — fréquence aberrante 44/j, E[R] -0.030 sur WF |
| `News_Fade` | ALLOWLIST | Gate REOPEN UNRESOLVED — E[R]≈-0.05, 94-100% session_end |
| `FVG_Fill_Scalp` | ALLOWLIST | functional_but_limited — E[R] négatif OOS |
| `Session_Open_Scalp` | ALLOWLIST | LAB ONLY — bloqué runtime edge |
| `Morning_Trap_Reversal` | ALLOWLIST / quarantine YAML | -12R lab 24m |
| `Liquidity_Sweep_Scalp` | ALLOWLIST / quarantine YAML | -9.8R |
| `London_Sweep_NY_Continuation` | DENYLIST | -326R |
| `Trend_Continuation_FVG_Retest` | DENYLIST | -22R |
| `BOS_Momentum_Scalp` | DENYLIST | -142R |
| `Power_Hour_Expansion` | DENYLIST | -31R |
| `Lunch_Range_Scalp` | DISABLED | Toxique |
| `DAY_Aplus_1_*` | DENYLIST | 0 trades (détection défaillante) |
| `SCALP_Aplus_1_*` | DENYLIST | 6 trades, 0 win, -1.4R |
| `IFVG_Flip_5m_Bull/Bear` | NON BRANCHÉ (research) | Smoke actif, aucune campagne OOS |
| A+ transcripts | Non chargé | research_only |

**Résumé :** 0 playbook promu. 0 edge validé. Tout est en phase backtest crédible.

---

## 7. Ce qui est DEFERRED / PAUSED (ne pas réactiver sans preuve)

- **NF arbitration / tp1** : gate REOPEN_1R_VS_1P5R fermé UNRESOLVED. Relancer
  uniquement si campagne NF dédiée sur fenêtre favorable détectée (nov 2025 standalone).
- **Wave 2 (FVG W2-1, Session_Open)** : research actif, ne pas mélanger avec validation
  noyau sans décision explicite.
- **NY capped (variante max_setups_per_session: 1)** : bloquée historiquement par sweep
  scoring nul. La plomberie est corrigée. Pas encore re-testée sur campagne longue.
- **A+ transcripts branchement** : `playbooks_Aplus_from_transcripts.yaml` non chargé
  volontairement. Research only.
- **Data longue (> 6 mois 2025)** : non encore disponible / validée.
- **UI / paper live / IBKR** : hors scope immédiat.

---

## 8. Ce qui ne doit surtout pas être touché

- `NY_Open_Reversal` YAML : ne pas modifier sans justification forte et campagne dédiée
- `paper_trading.py` : ne pas modifier sans raison explicite de cohérence moteur
- DENYLIST dans `risk_engine.py` : ne pas promouvoir sans preuve campagne
- La hiérarchie sources de vérité (voir `CLAUDE.md`) : ne pas court-circuiter

---

## 9. Prochaine tâche unique recommandée

**Statut actuel : fix perf moteur revalidé sur HEAD courant ; campagne OOS IFVG 5m relancée et auditable.**

Si on reprend plus tard, la suite logique n'est pas de refaire la même campagne à l'identique, mais de traiter la limite de couverture du split final ou d'ouvrir une nouvelle fenêtre de données. Le pipeline IFVG 5m reste actif et non validé comme edge.

---

## 10. FULL baseline comparable (campagne courte, protocole standard)

**Objectif :** obtenir une baseline labo FULL *comparable* (fenêtre fixe, protocole fixe, portefeuille explicite), sans SAFE/paper/live.

**Règle unique de sélection (depuis la cartographie FULL) :**
- `source=CORE` ∩ `policy_runtime=allowlist (AGGRESSIVE)` ∩ `not quarantined`

**YAML baseline (verbatim depuis knowledge/playbooks.yml) :**
- `backend/knowledge/campaigns/campaign_full_baseline_allow_core_no_quarantine.yml`
  - Playbooks : `NY_Open_Reversal`, `News_Fade`, `FVG_Fill_Scalp`, `Session_Open_Scalp`

**Run baseline (SPY only) :**
- Output-parent : `backend/results/labs/mini_week/full_baseline_allow_core_no_quarantine_sep08_sep26_2025/`
  - Label : `baseline_full_sep08_sep26_2025`
  - Fenêtre : `2025-09-08 → 2025-09-26`
  - Preuve `git_sha` (run_manifest) : `fbf19ac...`
  - Audit : `campaign_audit.json` → `overall_ok=true`, `data_coverage_ok=true`, `total_trades=2690`
  - Rollup : `campaign_rollup.json` → `total_trades_sum=2690`, `expectancy_r_weighted_by_trades=-0.0183097`, `profit_factor=0.3643575`, `final_capital=341.6104`

**Run baseline (SPY+QQQ) :**
- Output-parent : `backend/results/labs/mini_week/full_baseline_allow_core_no_quarantine_sep08_sep26_2025_spy_qqq/`
  - Label : `baseline_full_sep08_sep26_2025_spy_qqq`
  - Fenêtre : `2025-09-08 → 2025-09-26` (identique)
  - Commande exacte :
    ```bash
    cd /home/dexter/dexterio1-main/backend
    .venv/bin/python scripts/run_mini_lab_week.py \
      --start 2025-09-08 --end 2025-09-26 \
      --symbols SPY,QQQ \
      --playbooks-yaml knowledge/campaigns/campaign_full_baseline_allow_core_no_quarantine.yml \
      --output-parent full_baseline_allow_core_no_quarantine_sep08_sep26_2025_spy_qqq \
      --label baseline_full_sep08_sep26_2025_spy_qqq
    ```
  - Preuve `git_sha` (run_manifest) : `c008b42...`
  - Audit : `campaign_audit.json` → `overall_ok=true`, `data_coverage_ok=true`, `total_trades=3139`
  - Rollup : `campaign_rollup.json` → `total_trades_sum=3139`, `expectancy_r_weighted_by_trades=-0.0147993`, `profit_factor=0.2072468`, `final_capital=-798.7882`

**Comparaison minimale (même YAML, même fenêtre) :**
- SPY-only : `overall_ok=true`, `data_coverage_ok=true`, `total_trades_sum=2690`, `E[R]=-0.0183097`, `PF=0.3643575`, `final_capital=341.6104`
- SPY+QQQ : `overall_ok=true`, `data_coverage_ok=true`, `total_trades_sum=3139`, `E[R]=-0.0147993`, `PF=0.2072468`, `final_capital=-798.7882`

**Run baseline (SPY+QQQ) — fenêtre 2 adjacente :**
- Output-parent : `backend/results/labs/mini_week/full_baseline_allow_core_no_quarantine_sep29_oct17_2025_spy_qqq/`
  - Label : `baseline_full_sep29_oct17_2025_spy_qqq`
  - Fenêtre : `2025-09-29 → 2025-10-17`
  - Commande exacte :
    ```bash
    cd /home/dexter/dexterio1-main/backend
    .venv/bin/python scripts/run_mini_lab_week.py \
      --start 2025-09-29 --end 2025-10-17 \
      --symbols SPY,QQQ \
      --playbooks-yaml knowledge/campaigns/campaign_full_baseline_allow_core_no_quarantine.yml \
      --output-parent full_baseline_allow_core_no_quarantine_sep29_oct17_2025_spy_qqq \
      --label baseline_full_sep29_oct17_2025_spy_qqq
    ```
  - Preuve `git_sha` (run_manifest) : `1688cd1...`
  - Audit : `campaign_audit.json` → `overall_ok=true`, `data_coverage_ok=true`, `total_trades=571`
  - Rollup : `campaign_rollup.json` → `total_trades_sum=571`, `expectancy_r_weighted_by_trades=-0.0701702`, `profit_factor=0.0124196`, `final_capital=-7144.2440`

**Comparaison inter-fenêtres (SPY+QQQ, même YAML, fenêtres adjacentes) :**
- WIN1 `2025-09-08 → 2025-09-26` : `overall_ok=true`, `data_coverage_ok=true`, `total_trades_sum=3139`, `E[R]=-0.0147993`, `PF=0.2072468`, `final_capital=-798.7882`
- WIN2 `2025-09-29 → 2025-10-17` : `overall_ok=true`, `data_coverage_ok=true`, `total_trades_sum=571`, `E[R]=-0.0701702`, `PF=0.0124196`, `final_capital=-7144.2440`

**Run baseline (SPY+QQQ) — fenêtre 3 adjacente :**
- Output-parent : `backend/results/labs/mini_week/full_baseline_allow_core_no_quarantine_oct20_nov07_2025_spy_qqq/`
  - Label : `baseline_full_oct20_nov07_2025_spy_qqq`
  - Fenêtre : `2025-10-20 → 2025-11-07`
  - Commande exacte :
    ```bash
    cd /home/dexter/dexterio1-main/backend
    .venv/bin/python scripts/run_mini_lab_week.py \
      --start 2025-10-20 --end 2025-11-07 \
      --symbols SPY,QQQ \
      --playbooks-yaml knowledge/campaigns/campaign_full_baseline_allow_core_no_quarantine.yml \
      --output-parent full_baseline_allow_core_no_quarantine_oct20_nov07_2025_spy_qqq \
      --label baseline_full_oct20_nov07_2025_spy_qqq
    ```
  - Preuve `git_sha` (run_manifest) : `80573ee...`
  - Audit : `campaign_audit.json` → `overall_ok=true`, `data_coverage_ok=true`, `total_trades=3119`
  - Rollup : `campaign_rollup.json` → `total_trades_sum=3119`, `expectancy_r_weighted_by_trades=-0.0184387`, `profit_factor=0.5006682`, `final_capital=-9548.7720`

**Comparaison inter-fenêtres (SPY+QQQ, même YAML) — WIN1 vs WIN2 vs WIN3 :**
- WIN1 `2025-09-08 → 2025-09-26` : `overall_ok=true`, `data_coverage_ok=true`, `total_trades_sum=3139`, `E[R]=-0.0147993`, `PF=0.2072468`, `final_capital=-798.7882`
- WIN2 `2025-09-29 → 2025-10-17` : `overall_ok=true`, `data_coverage_ok=true`, `total_trades_sum=571`, `E[R]=-0.0701702`, `PF=0.0124196`, `final_capital=-7144.2440`
- WIN3 `2025-10-20 → 2025-11-07` : `overall_ok=true`, `data_coverage_ok=true`, `total_trades_sum=3119`, `E[R]=-0.0184387`, `PF=0.5006682`, `final_capital=-9548.7720`


## 10. Commandes exactes pour reprendre

```bash
cd /home/dexter/dexterio1-main/backend

# Repro minimale du blocage, fenêtre resserrée autour de BAR 33800
.venv/bin/python scripts/run_mini_lab_week.py \
  --start 2025-09-29 --end 2025-10-02 \
  --symbols SPY \
  --playbooks-yaml knowledge/campaigns/campaign_smoke_ifvg_5m.yml \
  --output-parent ifvg_probe_sep29_oct02 \
  --label ifvg_sep29_oct02

# Dry-run du walk-forward IFVG OOS avant la campagne longue
.venv/bin/python scripts/run_walk_forward_mini_lab.py \
  --start 2025-06-01 --end 2025-11-28 \
  --output-parent ifvg_oos_jun_nov2025 \
  --playbooks-yaml knowledge/campaigns/campaign_ifvg_5m_oos_jun_nov2025.yml \
  --dry-run

# Exécution OOS réelle sur les splits disponibles
.venv/bin/python scripts/run_mini_lab_week.py \
  --start 2025-08-30 --end 2025-10-13 \
  --label wf_s0_test \
  --output-parent ifvg_oos_jun_nov2025 \
  --playbooks-yaml knowledge/campaigns/campaign_ifvg_5m_oos_jun_nov2025.yml
.venv/bin/python scripts/run_mini_lab_week.py \
  --start 2025-10-14 --end 2025-11-28 \
  --label wf_s1_test \
  --output-parent ifvg_oos_jun_nov2025 \
  --playbooks-yaml knowledge/campaigns/campaign_ifvg_5m_oos_jun_nov2025.yml
```

---

## 11. Tests à lancer

```bash
# Validation minimale autour de la fenêtre problématique
cd /home/dexter/dexterio1-main/backend && .venv/bin/python scripts/run_mini_lab_week.py \
  --start 2025-09-29 --end 2025-10-02 \
  --symbols SPY \
  --playbooks-yaml knowledge/campaigns/campaign_smoke_ifvg_5m.yml \
  --output-parent ifvg_probe_sep29_oct02 \
  --label ifvg_sep29_oct02

# Validation campagne OOS IFVG 5m
cd /home/dexter/dexterio1-main/backend && .venv/bin/python scripts/run_mini_lab_week.py \
  --start 2025-10-14 --end 2025-11-28 \
  --label wf_s1_test \
  --output-parent ifvg_oos_jun_nov2025 \
  --playbooks-yaml knowledge/campaigns/campaign_ifvg_5m_oos_jun_nov2025.yml

# Audit et rollup de la campagne
cd /home/dexter/dexterio1-main/backend && .venv/bin/python scripts/audit_campaign_output_parent.py \
  --output-parent ifvg_oos_jun_nov2025
cd /home/dexter/dexterio1-main/backend && .venv/bin/python scripts/rollup_campaign_summaries.py \
  --path results/labs/mini_week/ifvg_oos_jun_nov2025
```

---

## 12. Risques / bugs connus

| Risque | Niveau | Note |
|--------|--------|------|
| Data source s'arrête au 2025-11-28 21:59 UTC | Moyen | Le split final du WF OOS reste non strictement couvert, ce n'est pas un bug moteur. |
| IFVG strength floor 0.65 = arbitraire | Moyen | Valeur choisie pragmatiquement. À calibrer si une campagne plus longue est disponible. |
| `_determine_direction` IFVG : nommage strict | Bas | Fonctionne si playbook_name contient BULL/BEAR. Fragile si renommage. |
| time_stop dominant P2 (6/10) | À surveiller | Setups n'atteignent pas TP sur cette fenêtre. Peut indiquer TP trop loin ou zone trop courte. |
| Sweep détecteur 1m très sélectif | Bas | Design voulu (stop-hunt strict). Aug 4-8 = 0 sweeps = normal. |
| `aplus_playbooks` chargés même avec loader IFVG | Bas | PlaybookLoader charge toujours aplus_path par défaut. Pas bloquant mais pollue les évaluations. |
| engine.py `run_name None` | Corrigé | Guard ajouté. |
| NY_Open_Reversal fréquence aberrante | Haut | 44 trades/jour max 148/j. Root cause non résolue. Variante capped non validée. |
| Toutes campagnes core-3 négatives | Structurel | Aucun edge prouvé. Direction = continuer exploration 5m/IFVG/HTF avant promotion. |

---

## 13. PROMPT POUR CODEX

```
Tu reprends DexterioBOT — algo trading SP500/NQ — dans /home/dexter/dexterio1-main.

ÉTAT : passe P1b/P2 terminée, fixes non commités. Committer d'abord (voir
section 10 de CODEX_HANDOFF.md).

DIRECTION UNIQUE :
  backtest crédible → campagnes comparables → portefeuille discipliné → paper limité

VÉRITÉ ACTUELLE :
- Aucun playbook n'a prouvé un edge positif. Tout est en backtest lab.
- Core-3 OOS jun-nov 2025 : toutes variantes négatives (E[R] -0.027 à -0.039).
- Le MASTER (71 transcripts ICT) est D/4H → 15m/5m setup → 1m exécution.
  Les playbooks 1m natifs compressent trop. IFVG 5m est plus aligné.
- IFVG 5m pipeline : actif (smoke 10 trades B/A). Pas d'edge validé.

PROCHAINE TÂCHE UNIQUE :
  Campagne OOS IFVG 5m sur enveloppe complète jun-nov 2025 (SPY+QQQ).
  Utiliser la chaîne campagne : preflight → campaign YAML → run WF → compare →
  gate verdict. Rester sur fenêtre NY 09:30-11:30 uniquement.

NE PAS :
- Toucher NY_Open_Reversal YAML sans campagne dédiée
- Toucher paper_trading.py sans raison explicite
- Promouvoir un playbook sans preuve campagne
- Partir sur NF / Wave2 / UI / IBKR / refonte moteur

FICHIERS CLÉS :
  CLAUDE.md                                  ← règles absolues repo
  backend/docs/ROADMAP_DEXTERIO_TRUTH.md     ← vérité état projet
  backend/docs/BACKTEST_CAMPAIGN_LADDER.md   ← procédure campagnes
  backend/engines/risk_engine.py             ← ALLOWLIST / DENYLIST
  backend/knowledge/campaigns/               ← YAMLs campagnes
  backend/engines/playbook_loader.py         ← scoring + évaluation
  backend/engines/setup_engine_v2.py         ← génération setups

COMMANDES :
  source .venv/bin/activate && cd backend
  python3 run_p2_ifvg_smoke.py               ← vérifier pipeline IFVG
  python3 scripts/backtest_data_preflight.py --start 2025-06-01 --end 2025-11-30
```
