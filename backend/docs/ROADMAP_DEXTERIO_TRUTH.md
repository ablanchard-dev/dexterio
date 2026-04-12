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
| Roadmap NF (stop / tp1) | `PHASE_A_NF_STOP_DECISION.md`, `PHASE_B_*`, docs arbitration | A **clos** ; B/C **gates** | **Actif** (décision) | `REOPEN_1R_VS_1P5R` etc. | **Hors scope backtest** sauf campagne YAML dérivée déjà supportée |
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

## NEXT STEP

1. Utiliser `campaign_gate_verdict` + ladder contract pour chaque campagne (`--manifest-only` si summary absent).
2. CI : workflow `.github/workflows/backtest-campaign-tools.yml` + `scripts/backtest_campaign_smoke.py`.
