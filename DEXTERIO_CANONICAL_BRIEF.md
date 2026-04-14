# DEXTERIO — Brief Canonique

> Document de cadrage unique pour toute session de travail sur ce repo.
> À envoyer en contexte à Claude avant chaque session.
> Dernière mise à jour : 2026-04-14

---

## 1. IDENTITÉ DU PROJET

**DexterioBOT** est un bot de trading algorithmique pour **SP500 (SPY/ES)** et **Nasdaq (QQQ/NQ)** en intraday.
Stratégies : **ICT / Smart Money** (FVG, IFVG, Order Block, Breaker Block, Liquidity Sweep, BOS).

**Chemin local** : `/home/dexter/dexterio1-main`
**Stack** : Python / FastAPI / MongoDB (backend) + React / Tailwind (frontend)
**Environnement** : Linux Ubuntu, venv → `backend/.venv/`

---

## 2. DIRECTION IMPOSÉE

```
backtest crédible sur vraies données
    → campagnes comparables
        → portefeuille discipliné
            → paper limité honnête
                → live plus tard
```

**Ne jamais dériver de cette direction.**

---

## 3. HIÉRARCHIE DES SOURCES DE VÉRITÉ

En cas de conflit entre documents, cet ordre prime :

1. `backend/docs/ROADMAP_DEXTERIO_TRUTH.md`
2. `backend/docs/BACKTEST_CAMPAIGN_LADDER.md`
3. `backend/engines/risk_engine.py` (AGGRESSIVE_ALLOWLIST / DENYLIST)
4. `backend/docs/CORE_PAPER_NOW_LAUNCH.md`
5. `backend/docs/ROADMAP_SAFE_FULL_PORTFOLIO.md`

Tous les autres docs sont des **preuves ou historiques** — ils ne priment pas.

---

## 4. ARCHITECTURE TECHNIQUE RÉELLE

```
data parquet 1m (SPY/QQQ)
    ↓ TimeframeAggregator (1m → 5m, 15m, 1H, 4H, D)
    ↓ MarketState (session, HTF bias, day_type, regime)
    ↓ SetupEngineV2 (patterns, scoring, filtres edge)
    ↓ PlaybookLoader (YAML → triggers, filtres session/grade)
    ↓ RiskEngine (allowlist/denylist, guardrails, sizing)
    ↓ BacktestEngine (replay, coûts, parquet trades)
    ↓ MiniLabSummary / Manifest / Parquet
    ↓ CampaignGateVerdict
```

**Filtres edge actifs dans SetupEngineV2** : rejet `regime_chop`, `no_liquidity_event`, `rr_too_low`.

**Coûts** : intégrés dans `backend/backtest/costs.py`.

---

## 5. CHAÎNE CAMPAGNE OPÉRATIONNELLE

Tous ces outils sont dans `backend/scripts/` :

| Outil | Rôle |
|-------|------|
| `backtest_data_preflight.py` | Couverture data avant run long |
| `run_mini_lab_week.py` / `run_mini_lab_multiweek.py` | Exécution campagnes |
| `walk_forward_light.py` + `run_walk_forward_mini_lab.py` | OOS splits |
| `compare_mini_lab_summaries.py` | Diff JSON entre runs |
| `backtest_leakage_audit.py` | Anti-leakage |
| `campaign_gate_verdict.py` | Verdict go/no-go (`NOT_READY` / `BACKTEST_READY` / `LIMITED_PAPER`) |
| `audit_campaign_output_parent.py` | Audit artefacts campagne |
| `rollup_campaign_summaries.py` | Σ multi-runs, E[R] pondéré |
| `postmortem_campaign_trades.py` | Post-mortem quant |

**Métrique principale** : `trade_metrics_parquet.expectancy_r` — **pas** `final_capital`.

---

## 6. ÉTAT DU PORTEFEUILLE PLAYBOOKS

### Taxonomie

- `functional_now` — actif, prouvé, protéger
- `functional_but_limited` — branché, sous surveillance
- `quarantined` — stats négatives, lab dédié requis avant usage
- `blocked_by_policy` — deny code, hors scope
- `research_only` — non chargé, jamais testé
- `do_not_promote` — prouvé négatif, abandon

### Tableau de vérité

| Playbook | Statut code | Catégorie | Résultat campagne | Gate / Blocage |
|----------|-------------|-----------|-------------------|----------------|
| `NY_Open_Reversal` | ALLOWLIST | `functional_now` | Seul survivant relatif OOS — ne pas toucher YAML | Aucun. **Protéger.** |
| `News_Fade` | ALLOWLIST | `functional_but_limited` / sous gate | +90R historique, E[R] agrégé négatif à 1R vs ref nov | **Gate REOPEN_1R_VS_1P5R** ouvert. Sweep tp1 requis. |
| `FVG_Fill_Scalp` | ALLOWLIST | `functional_but_limited` | E[R] négatif core-3 ; porteur majeur de dérive | Patch W2-1 déployé. Labs dédiés requis. |
| `Session_Open_Scalp` | ALLOWLIST | `functional_but_limited` / **LAB ONLY** | READY_WITH_LIMITATIONS | **Bloqué runtime edge** (BASELINE_EDGE_STATE 2026-04-09) |
| `Morning_Trap_Reversal` | ALLOWLIST code / quarantine YAML | `quarantined` | -12.1R net (24m lab) | Lab dédié avant tout usage |
| `Liquidity_Sweep_Scalp` | ALLOWLIST code / quarantine YAML | `quarantined` | -9.8R net, 492 trades | Lab dédié ou abandon |
| `London_Sweep_NY_Continuation` | **DENYLIST** | `do_not_promote` | **-326R** | Abandon définitif |
| `Trend_Continuation_FVG_Retest` | **DENYLIST** | `do_not_promote` | -22.32R (nov 2025) | Abandon définitif |
| `BOS_Momentum_Scalp` | **DENYLIST** | `do_not_promote` | **-142R** | Abandon définitif |
| `Power_Hour_Expansion` | **DENYLIST** | `do_not_promote` | -31R | Abandon définitif |
| `Lunch_Range_Scalp` | DISABLED (YAML) | `do_not_promote` | Toxique | Abandon définitif |
| `DAY_Aplus_1_Liquidity_Sweep_OB_Retest` | **DENYLIST** | `blocked_by_policy` | Sweep/BOS non détectés → 0 trades | Hors scope |
| `SCALP_Aplus_1_Mini_FVG_Retest_NY_Open` | **DENYLIST** + quarantine | `blocked_by_policy` | 6 trades, 0 win, -1.4R | Hors scope |
| A+ transcripts (`playbooks_Aplus_from_transcripts.yaml`) | **Non chargé** | `research_only` | Jamais testé | Branchement volontaire requis |

---

## 7. RÉSULTATS CAMPAGNES RÉCENTES (VÉRITÉ OOS)

**Campagne core-3 OOS SPY/QQQ 1m, jun–nov 2025, 2 plis OOS** :

| Variante | Dossier lab | E[R] pondéré | Trades | Verdict |
|----------|-------------|-------------|--------|---------|
| Trio NY+FVG+Session | `wf_core3_oos_jun_nov2025` | **-0.027** | ~2780 | Négatif |
| Grades resserrés | `wf_core3_tune_stricter_grades` | **≈ -0.027** | ~2780 | Aucun delta |
| Sans FVG (NY+Session) | `wf_core3_no_fvg` | **-0.030** | -42% | Pire global ; s1 meilleur, s0 pire |
| FVG seul | `wf_core3_fvg_only` | **-0.039** | ~1686 | Pire variante |
| NY seul | `wf_core3_ny_only` | split s0/s1 différent | réduit | Pas de validation agrégat simple |

**Décision produit** : ne pas remplacer le trio par une simplification sans critère de régime/split. Poursuivre par YAML dérivés + même chaîne gate.

**Runs de référence récents** (2026-04-09, dossier `backend/results/ref_runs/`) :
- `ref_validation_20260409` — SPY, 2025-08-04, 10 trades, validation courte
- `edge_filter_validation_20260409` (a/b/c/d) — variantes filtres edge
- `edge_sprint_short_20260409` — run court sprint

---

## 8. SAVOIR MASTER — POINTS CLÉS

**Le MASTER** (`/home/dexter/Documents/MASTER_FINAL.txt` et `/home/dexter/dexterio1-main/data/MASTER_FINAL.txt`) est une compilation de 71 transcripts YouTube ICT/smart money (~48k lignes).

**Vérité timeframe critique** :
> Le MASTER n'est pas 1m natif. La logique conceptuelle est **D/4H bias → 15m/5m setup → 1m exécution**.
> Les playbooks actuels (FVG_Fill_Scalp, NY_Open_Reversal, etc.) sont conceptuellement des setups 5m ou 15m/5m, mais le moteur les évalue sur 1m → trop de bruit, fréquence trop haute.

**Setup families identifiées dans le MASTER** :

| Famille | Timeframes réels | Lien repo actuel |
|---------|-----------------|-----------------|
| Sweep + IFVG flip (inversion FVG invalidé) | context 1H/4H, setup 5m, entry 1m | `Aplus_01` transcript (research-only) |
| HTF Bias + 15m BOS + confluence OB/FVG | D/4H, setup 15m, entry 5m/1m | `Aplus_04` transcript (research-only) |
| FVG Fill limit order propre | setup 5m, limit order 5m | `FVG_Fill_Scalp` (mal calibré 1m) |
| Opening Range Breakout + Marubozu | context 5m, entry 1m | `Session_Open_Scalp` (LAB ONLY) |
| News Spike Fade | 1m natif réel | `News_Fade` (sous gate tp1) |

**Savoir branché mais mal aligné** : FVG_Fill_Scalp, NY_Open_Reversal — concepts 5m compressés en 1m.
**Savoir non branché** : IFVG 5m, HTF+15m BOS — uniquement dans `playbooks_Aplus_from_transcripts.yaml` (research-only).

---

## 9. RÈGLES ABSOLUES DE TRAVAIL

**Ne jamais :**
- Migrer Dexterio vers un autre framework
- Lancer une refonte front ou un rewrite Rust
- Toucher `paper_trading.py` sans raison explicite
- Replonger dans NF/TP/breakeven/session_end sauf priorité active
- Modifier `NY_Open_Reversal` côté moteur sans justification très forte
- Modifier Wave 2 ou le YAML canonique NF sans gate claire
- Promouvoir des playbooks sans preuve
- Supposer que 1m = vérité stratégique universelle

**Toujours :**
- Garder Dexterio comme socle
- Travailler à partir du repo réel
- Respecter les décisions déjà prises
- Distinguer : preuve repo / preuve artefact / hypothèse / intuition / décision
- Utiliser `expectancy_r` comme métrique principale (pas `final_capital`)
- Une variante = un artefact versionné (YAML sous `knowledge/campaigns/` + commit)

---

## 10. PRIORITÉS ACTUELLES

### P0 — Clore gate tp1 News_Fade
**Quoi** : sweep YAML dérivé `tp1_rr=1.0` vs `tp1_rr=1.5` sur les 12 fenêtres `nf1r_confirm_*`.
**Pourquoi** : gate ouvert depuis des mois, bloque toute campagne paper NF sérieuse.
**Comment** : script sweep existant (PHASE B runner), données disponibles, rollup + décision.
**Résultat attendu** : décision ferme tp1, YAML NF figé, campagne NF dédiée possible.

### P1 — Campagne NY_Open_Reversal isolé
**Quoi** : run campagne NY-only, fenêtre la plus longue possible, avec gate verdict.
**Pourquoi** : NY est le seul noyau. Doit être prouvé positif en isolation avant tout ajout.
**Comment** : dériver `campaign_wf_core3_ny_only.yml`, preflight, multiweek, rollup, gate.
**Résultat attendu** : verdict clair sur l'edge NY. Base pour la suite.

### P2 — Explorer IFVG 5m (Aplus_01/03)
**Quoi** : prototyper playbook YAML avec `confirmation_tf: "5m"` + détection IFVG sur 5m.
**Pourquoi** : opportunity non testée la plus alignée avec le savoir MASTER.
**Prérequis** : lire `engines/patterns/ifvg.py`, vérifier support multi-tf dans pipeline.
**Résultat attendu** : smoke 1 jour → go/no-go sur faisabilité technique.

---

## 11. HORS SCOPE IMMÉDIAT

- UI / frontend cockpit
- Live IBKR
- Nouvelles couches d'outillage
- Refonte moteur
- NF chantier TP/breakeven/session_end
- Wave 2 (FVG W2-2, Session_Open élargissement)
- A+ transcripts branchement tant que P0/P1 non clos
