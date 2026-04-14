# Roadmap Dexterio — vérité unique (réconciliation)

**Source de vérité officielle pour « où on en est » : ce fichier**, complété par :

1. **Chaîne backtest / campagnes** → `BACKTEST_CAMPAIGN_LADDER.md` + scripts listés dedans.
2. **Politique playbooks live / risk** → `engines/risk_engine.py` (`AGGRESSIVE_ALLOWLIST` / `AGGRESSIVE_DENYLIST`) + `knowledge/playbook_quarantine.yaml` (référence historique ; le code deny/allow prime pour l’exécution).
3. **Paper honnête** → `CORE_PAPER_NOW_LAUNCH.md` + `ROADMAP_SAFE_FULL_PORTFOLIO.md`.

Les autres documents sont **des preuves ou des plans historiques** ; en cas de conflit, **ne pas** les préférer à la hiérarchie ci-dessus sans mise à jour explicite de ce fichier.

---

## Contradictions résolues

| Conflit | Résolution |
|---------|------------|
| `ROADMAP_COMPLETE.md` Phase B « 0 % » vs code avec `backtest/costs.py` + tests | **Résolu (doc 2026-04)** : coûts = **code** ; la **Phase B** de `ROADMAP_COMPLETE.md` décrit désormais le **livré** (chemins `backend/backtest/*`, `backend/tests/test_backtest_costs.py`). |
| `PHASE_4_D27_*.md` « phases 5–8 ouvertes » vs `PHASES_4_8_POINTER.md` « 4–8 couvertes » | **Les deux vrais :** jalons **doc/tech** des phases 5–8 **faits** (preuves parquet SAFE nov, doc FULL, Phase 7 vol/day_type, tests coûts). **Gates produit** (SAFE multi-mois, FULL discipliné, paper large) **encore ouverts**. |
| Quarantaine YAML vs allowlist code pour `Morning_Trap_Reversal` | **Allowlist code** : MTR est **dans** `AGGRESSIVE_ALLOWLIST`. Le YAML quarantaine liste des **historiques stats** ; alignement produit = sujet **campagne**, pas ambiguïté d’exécution : le moteur autorise MTR si allowlist + risk OK. |
| `Trend_Continuation_FVG_Retest` dans `playbooks.yml` mais bloqué | **DENYLIST** + retiré de l’allowlist → **non promouvable** en AGGRESSIVE tant que la policy n’est pas changée **explicitement** dans `risk_engine.py`. |

---

## Tableau unique des axes (roadmap truth)

| Axe (chantier) | Fichier source de vérité | Statut réel | Obsolète / partiel / actif | Blocages produit | Prochaine action |
|----------------|---------------------------|-------------|----------------------------|------------------|------------------|
| ZIP8 → prod A–E | `ROADMAP_COMPLETE.md` | Vision A–E ; **Phase B coûts à jour** | **Partiellement obsolète** (surtout C–E tant non implémentés) | UI/paper/VPS non câblés comme dans le plan | **Coûts** = code + section Phase B du fichier racine ; **campagnes** = ladder + ce fichier |
| Phases 0–8 audit / portfolio | `PHASES_4_8_POINTER.md` + `PHASE_*` | Jalons **faits** ; gates **ouverts** | **Actif** (interprétation) | SAFE « elite » non prouvé sur longue plage ; FULL expansion | Enchaîner **campagnes ladder** + OOS, pas reparcourir les phases en boucle |
| SAFE / FULL / CORE_PAPER | `ROADMAP_SAFE_FULL_PORTFOLIO.md` + `CORE_PAPER_NOW_LAUNCH.md` | **Actif** | **Actif** | NF tp1 arbitrage ; FVG stabilité multi-fenêtre | Sweeps documentés ; paper **limité** seulement si gate |
| Roadmap NF (stop / tp1) | `PHASE_A_NF_STOP_DECISION.md`, `PHASE_B_*`, docs arbitration | A **clos** ; B **clos UNRESOLVED** (2026-04-14) | **Actif** (décision) | Gate `REOPEN_1R_VS_1P5R` **fermé UNRESOLVED** : les deux bras négatifs E[R]≈-0.05, 94-100% sess_end → tp1 jamais atteint → question 1.0R vs 1.5R **inopérante sur aug/sep/oct 2025**. NF nécessite une campagne dédiée fenêtre favorable (ex. nov 2025). | Ne pas relancer sweep tp1 — relancer si campagne NF sur fenêtre positive détectée (p.ex. nov 2025 standalone) |
| Wave 2 (FVG W2-1, Session_Open) | `WAVE2_*` docs | **Actif** recherche | **Actif** | Stabilité > 1 semaine si exigé | Labs dédiés ; **ne pas** mélanger avec validation longue « noyau » sans décision |
| Backtest crédible & campagnes | `BACKTEST_CAMPAIGN_LADDER.md` + `backtest_data_preflight` + manifests | **Actif** ; outillage **récent** | **Actif** | Données 1–2 ans complètes ; OOS systématique | Preflight strict ; WF ; compare ; `campaign_gate_verdict` |
| Contrats / paper preflight | `contracts/`, `paper_preflight`, `paper_supervised_precheck`, `TradeRowV0` | **Actif** | **Actif** | — | Utiliser en **amont** paper limité |
| A+ YAML chargés | `aplus_setups.yml` + loader | **DAY_…** et **SCALP_…** dans loader | **Actif** | **SCALP A+** en **DENYLIST** ; DAY A+ en deny | Ne pas promouvoir A+ **sans** relecture risk |
| A+ transcripts | `playbooks_Aplus_from_transcripts.yaml` | **Non chargé** par le loader | **Research only** | Branchement volontaire requis | Hors promotion tant que non câblé |

---

## Clos techniquement vs clos doc seulement vs ouvert produit

- **Clos techniquement :** Phase 3B exécution cœur Wave1, coûts dans backtest, instrumentation Phase 7 dans le moteur de setups, preflight + manifest `data_coverage`, compare/WF/audit scripts, `trade_metrics_parquet` dans summary (quand parquet présent).
- **Clos doc seulement :** plusieurs `PHASE_*.md` qui **décrivent** un état sans engagement live ; `PHASE_6_FULL_MODE` principes sans allowlist élargie automatique.
- **Ouvert produit :** paper large, SAFE 4–5 snipers **prouvés** multi-régimes, NF promotion noyau, live IBKR, UI cockpit — **gates** dans `CORE_PAPER_NOW` / ladder.

---

## DÉCISION

La **roadmap unique** opérationnelle pour DexterioBOT aujourd’hui est :

**`ROADMAP_DEXTERIO_TRUTH.md` (ce fichier) + `BACKTEST_CAMPAIGN_LADDER.md` + `risk_engine.py` + `CORE_PAPER_NOW_LAUNCH.md`.**

`ROADMAP_COMPLETE.md` reste la **vision ZIP8 → prod** (phases A–E) ; la **Phase B (net-of-costs)** y est **alignée** sur le code (pas seulement le bandeau).

---

## Synthèse campagnes WF `core-3` (données SPY/QQQ 1m, enveloppe 2025-06-03 → 2025-11-27, 2 plis OOS test)

Référence baseline : `results/labs/mini_week/wf_core3_oos_jun_nov2025/` + `results/campaigns/wf_core3_oos_jun_nov2025/POSTMORTEM_QUANT.json`.

| Variante YAML | Dossier lab | Fait mesurable clé |
|---------------|-------------|-------------------|
| Trio NY+FVG+Session | `wf_core3_oos_jun_nov2025` | E[R] pondéré ≈ **-0,027** ; **~2780** trades ; SL domine en ΣR. |
| `grade_thresholds` resserrés | `wf_core3_tune_stricter_grades` | **Aucun delta** funnel / nombre de trades (levier abandonné). |
| Sans FVG (NY+Session) | `wf_core3_no_fvg` | **-42 %** trades, **E[R] global ≈ -0,030** (pire) ; **s1** beaucoup mieux, **s0** pire ; moins de SL en **nombre**, ΣR SL plus négatif. |
| FVG seul | `wf_core3_fvg_only` | **~1686** trades, E[R] pondéré ≈ **-0,039** ; **s0** et **s1** tous deux négatifs (pas de compensation type no-FVG sur s1). |

**Décision provisoire produit** : ne pas remplacer le trio par « NY+Session seul » sur l’agrégat sans critère de régime/split ; poursuivre le tuning par **YAML dérivés** + même chaîne gate/rollup/postmortem, pas par nouveaux runners.

---

## Gate NF tp1 — verdict final (2026-04-14)

**Gate fermé : `KEEP_BOTH_UNRESOLVED_PENDING_MORE_DATA`**

Artefacts : `results/labs/mini_week/_nf_tp1_arbitration_aggregate.json` + `docs/PHASE_NF_TP1_ARBITRATION_TABLE.md`

| bras | NF trades | ΣR | E[R] |
|------|----------:|---------:|---------:|
| tp1 = 1.0R | 85 | -4.128 | **-0.0486** |
| tp1 = 1.5R | 85 | -3.439 | **-0.0405** |
| ΔE[R] | — | +0.069 | **+0.0081** |

Seuil d'équivalence ε = 0.015R. `|ΔE[R]| = 0.0081R < ε` → UNRESOLVED.

**Diagnostic réel** : le tp1 n'est pas le problème. Sur 12 fenêtres aug/sep/oct 2025, 94–100% des trades NF sortent par `session_end` avant d'atteindre tout TP. La question 1.0R vs 1.5R est **inopérante** sur cette période. E[R] négatif dans les deux bras.

**Ce que cela signifie** :
- NF a généré ~+90R sur la fenêtre PHASE B (nov 2025) — edge potentiellement présent mais régime-dépendant
- aug/sep/oct 2025 = pas d'edge NF, pas de TP atteint, session_end dominant
- Sweep tp1 à **ne pas relancer** sur les mêmes fenêtres

**Prochaine action NF** : campagne dédiée NF fenêtre favorable (nov 2025 standalone) pour confirmer si l'edge PHASE B est réel et reproductible. Pas avant P1 (NY isolé).

---

## NEXT STEP

1. **Gate campagne (process)** : pour chaque run visant une **promotion** sur l’échelle `BACKTEST_CAMPAIGN_LADDER.md`, exécuter `backend/scripts/campaign_gate_verdict.py` avec les options du niveau (voir la table « Contrat opérationnel » dans ce ladder). Sans `mini_lab_summary` encore disponible : `--manifest-only path/run_manifest.json`. Avec summary : `summary.json --manifest path/run_manifest.json` et, si le niveau l’exige, `--require-manifest-coverage` / `--require-trade-metrics`.
2. **CI outils campagne** : le workflow `.github/workflows/backtest-campaign-tools.yml` lance `backend/scripts/backtest_campaign_smoke.py` (pytest ciblé : couverture data, compare, gate, audit sorties, rollup). Déclenchement sur push/PR des chemins listés dans le YAML ; **exécution manuelle** via `workflow_dispatch` sur GitHub. Vérif locale : `cd backend && .venv/bin/python scripts/backtest_campaign_smoke.py`.
