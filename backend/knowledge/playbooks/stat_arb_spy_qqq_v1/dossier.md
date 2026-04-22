# Stat Arb SPY-QQQ v1 — dossier

> Standard industriel (plan §18). Sprint 3 du plan parsed-nibbling-kettle, branche **non-ICT** ouverte après Sprint 1 SMOKE_FAIL Aplus_01_full_v1 (2026-04-22).
> Statut, hypothèse, état décisionnel, dépendances moteur, kill rules — écrits **avant** code (§19 phase B).

---

## Pièce A — fiche d'identité

| Champ | Valeur |
|---|---|
| Nom canonique | `Stat_Arb_SPY_QQQ_v1` |
| Version | `v1` |
| Famille | non-ICT — stat arb / mean reversion sur spread coïntégré |
| Type | Multi-leg (2 jambes simultanées, beta-neutral) — stateful per-pair |
| Instruments | SPY (jambe 1) + QQQ (jambe 2). Pair fixe. |
| Timeframes | 5m (signal + exécution + suivi z-score) |
| Direction | both : `long_spread` (long SPY + short QQQ × β) si z < -seuil ; `short_spread` (short SPY + long QQQ × β) si z > +seuil |
| Régime visé | NY session 09:30–15:00 ET (liquidité maximale, exécution duale exécutable) |
| Statut initial | `SPECIFIED_BLOCKED_BY_INFRA` (le moteur actuel ne sait pas exprimer un trade multi-leg simultané beta-neutral — cf pièce D) |
| **Statut actuel** | **`ARCHIVED`** (SMOKE_FAIL nov_w4, 2026-04-22, 3/3 kill rules pré-écrites atteintes) |
| Auteur / origine | Plan parsed-nibbling-kettle §5.3 P3 + QUANT_SYNTHESIS §3.2 (insurance non-ICT post-pivot ICT) |
| Dernière review | 2026-04-22 (création dossier post-Sprint 1) |

---

## Pièce B — hypothèse formelle (5 sous-blocs, non négociables)

### Thèse
Le spread normalisé entre SPY et QQQ (deux ETFs sur indices US large-cap fortement corrélés mais non-identiques) est **mean-reverting** intraday quand il s'écarte significativement de sa moyenne mobile. Une déviation z-score > 2.0σ revient vers 0 dans les heures qui suivent, suffisamment souvent pour générer un edge tradable beta-neutral.

### Mécanisme
SPY et QQQ partagent un sous-jacent économique commun (US large-cap), donc leurs returns sont coïntégrés sur fenêtres intraday. Les déviations temporaires viennent d'asymétries de flux (rotation tech ↔ value, news sectorielle, market-on-close imbalance) qui se résolvent par arbitrage actif des market makers. Trader le spread = se positionner sur le **retour à la moyenne** de la composante stationnaire de leur relation, en neutralisant l'exposition directionnelle au marché US (β ajusté).

### Conditions de fertilité
- Coïntégration confirmée par Engle-Granger sur la fenêtre de calibration (p < 0.05).
- Résidus stationnaires (ADF p < 0.05) sur fenêtre rolling 20 bars 5m.
- Liquidité abondante sur les 2 jambes (NY session, pas de halts).
- Volatilité spread modérée — éviter les régimes de blow-out (z > 4σ → souvent regime change, pas mean-rev).

### Conditions de stérilité (ne pas trader)
- Lunch 12:00–13:00 ET (liquidité fragmentée, faux signaux).
- News window ±5min (FOMC, CPI, NFP, earnings tech géants — gaps).
- Coïntégration cassée (Engle-Granger p > 0.10 sur les 30 derniers jours rolling) — la relation structurelle est partie.
- z-score déjà > 3.0σ au moment de l'entrée (déjà en territoire blow-out, pas mean-rev).
- Lock-out post-stop : 30 min après un SL pour éviter de retrader la même divergence.

### Risque principal (= falsifiabilité)
**L'hypothèse est fausse si** : sur ≥30 setups émis sur 4 semaines NY corpus, **E[R] net+slippage < 0** et taux de mean-reversion (z atteint 0 avant SL) < 50%. Cela voudrait dire que les déviations z > 2σ ne sont **pas** mean-reverting — la relation SPY-QQQ n'a pas la stationnarité supposée intraday, ou les market makers arbitrent trop vite pour laisser une fenêtre tradable retail.

**L'hypothèse est aussi fausse si** : sur le smoke nov_w4, **0 setup émis** (seuils z trop serrés ou coïntégration absente sur la fenêtre) — Cas A/D §20 plutôt que Cas C.

---

## Pièce C — spécification d'état décisionnel

| Étape | Description |
|---|---|
| **Point d'armement** | À chaque close 5m : recompute z-score = (spread_now - rolling_mean_20) / rolling_std_20 où spread = log(SPY) - β × log(QQQ), β estimé par régression OLS sur les 60 derniers bars 5m. |
| **Point de confirmation** | `\|z\|` ≥ 2.0σ ET coïntégration Engle-Granger PASS sur fenêtre 60 bars (p < 0.05) ET z-score précédent du même côté (anti-flip). |
| **Point d'émission setup** | Si z ≤ -2.0 → setup `long_spread` (long SPY + short QQQ × β_hedge). Si z ≥ +2.0 → setup `short_spread` (short SPY + long QQQ × β_hedge). β_hedge = ratio dollars (SPY_qty × SPY_price = β × QQQ_qty × QQQ_price). |
| **Point d'invalidation (SL)** | `\|z\|` ≥ 3.0σ (blow-out) OU `\|z\|` continue de croître pendant 12 bars 5m (1h) après l'entrée sans toucher 0 (time-stop). |
| **Point d'exit (TP)** | `\|z\|` ≤ 0.5σ (mean-reversion atteinte). Pas de TP partiel — clôture des 2 jambes simultanément. |
| **Timeouts** | `cointegration_recompute`: tous les bars 5m. `entry_lockout_post_sl`: 30 min après SL pour la même paire. `max_hold_duration`: 90 min (18 bars 5m). |

**Pas de cascade séquentielle** — c'est un système **continu** : chaque close 5m réévalue. C'est l'inverse architectural d'Aplus_01 (rare, séquentiel) → naturellement plus dense, donc statistiquement plus testable sur 1 semaine.

---

## Pièce D — dépendances moteur + audit infra

### Détecteurs requis
| Brique | Statut | Note |
|---|---|---|
| `cointegration_test(series_a, series_b, window)` (Engle-Granger ADF) | **MISSING** | Nouveau module `backend/engines/stat_arb/cointegration.py`. Dépendance externe : `statsmodels.tsa.stattools.adfuller`. |
| `rolling_zscore(spread_series, lookback)` | **MISSING** | Module `backend/engines/stat_arb/zscore.py`. Pure fonction NumPy. |
| `beta_estimator(series_a, series_b, lookback)` (OLS rolling) | **MISSING** | Même module. |

### Trackers requis
| Brique | Statut | Note |
|---|---|---|
| `PairSpreadTracker(symbol_a, symbol_b)` per-pair state machine | **MISSING** | Module `backend/engines/stat_arb/pair_spread_tracker.py`. État : `IDLE`, `ARMED_LONG`, `ARMED_SHORT`, `IN_TRADE_LONG`, `IN_TRADE_SHORT`, `LOCKOUT_POST_SL`. Précédent : `Aplus01Tracker` per-symbol → ici per-pair. |

### Helpers
| Brique | Statut | Note |
|---|---|---|
| `pair_sizing(spy_price, qqq_price, beta, capital_allocation_$)` | **MISSING** | Calcule `(spy_qty, qqq_qty)` beta-neutral. |
| `simultaneous_dual_leg_open(setup_long, setup_short)` exécutable atomiquement | **MISSING** | **Bloquant majeur** — `ExecutionEngine` actuel ouvre 1 trade à la fois. Besoin d'un primitive `open_pair_atomic(setup_a, setup_b)` qui réussit ou échoue ensemble. |

### Logique de session
| Brique | Statut | Note |
|---|---|---|
| Session NY 09:30–15:00 ET filter | EXISTS | `session_range.py` + helper `get_session_tag` post-S1.1 timezone audit. |
| Lunch exclusion 12:00–13:00 ET | EXISTS | Param YAML `time_windows.exclude` standard. |

### SL / TP logic
| Brique | Statut | Note |
|---|---|---|
| `sl_logic: zscore_blowout` (custom) | **MISSING** | Pas un SL prix — un SL **z-score** (`\|z\|` ≥ threshold). Nouveau type. |
| `tp_logic: zscore_meanrev` (custom) | **MISSING** | Pas un TP RR — un TP z-score (`\|z\|` ≤ threshold). Nouveau type. |
| `time_stop` (max_hold_duration_minutes) | EXISTS | Standard YAML field. |

### Risk hooks particuliers
| Brique | Statut | Note |
|---|---|---|
| Pair-level cap (max 1 pair active à la fois) | **MISSING** | Nouveau hook risk_engine. |
| Capital allocation par pair (% NAV) | EXISTS | Standard sizing — adapter pour 2 jambes. |
| Margin requirement check (long + short = 2× margin) | **PARTIAL** | À auditer côté broker adapter futur. |

### Champs runtime journal requis
| Champ | Statut | Note |
|---|---|---|
| `pair_id` (string) | **MISSING** | Lien entre 2 trades de la même paire. |
| `leg_role` ("primary"/"hedge") | **MISSING** | |
| `entry_zscore`, `exit_zscore`, `cointegration_pvalue_at_entry`, `beta_at_entry` | **MISSING** | Pour audit + tuning. |

### Résultat audit infra

**Statut** : `SPECIFIED_BLOCKED_BY_INFRA`

**Briques manquantes critiques (chemin bloquant)** :
1. `simultaneous_dual_leg_open` — primitive atomique pair execution (le plus dur, touche `ExecutionEngine`).
2. `cointegration` + `zscore` + `beta_estimator` helpers (faciles, ~150 lignes total).
3. `PairSpreadTracker` state machine (template existe via Aplus01Tracker, ~200 lignes adapt).
4. `sl_logic: zscore_blowout` + `tp_logic: zscore_meanrev` custom resolvers.
5. Journal field extensions.

**Plan chantier (estimation)** :
- Phase D1 : helpers purs (cointegration, zscore, beta, sizing) + tests (1 jour).
- Phase D2 : `PairSpreadTracker` + tests (1 jour).
- Phase D3 : `simultaneous_dual_leg_open` primitive dans `ExecutionEngine` + tests (1.5 jours, le plus risqué — touche Phase W byte-identity).
- Phase D4 : custom z-score SL/TP resolvers + journal fields + YAML schema extension (0.5 jour).
- Phase D5 : YAML d'exécution (pièce E) + tests intégration (0.5 jour).
- Phase D6 : smoke nov_w4 + verdict (0.5 jour).

**Total estimé** : 5 jours cohérent avec plan §5.3 P3 (3–5 jours).

---

## Pièce E — YAML d'exécution (à écrire en phase D5)

À ce stade : **non écrit**. Schéma cible documenté en pièce C. Sera créé dans `backend/knowledge/campaigns/stat_arb_spy_qqq_v1.yml` en phase D5.

Champs prévus (esquisse, non normatifs tant que phase D1–D4 pas complétée) :
```yaml
name: Stat_Arb_SPY_QQQ_v1
version: v1
family: stat_arb
pair: [SPY, QQQ]
setup_tf: 5m
sessions:
  - {start: "09:30", end: "12:00", tz: "America/New_York"}
  - {start: "13:00", end: "15:00", tz: "America/New_York"}
cointegration:
  method: engle_granger
  window_bars: 60
  pvalue_threshold: 0.05
zscore:
  lookback_bars: 20
  entry_threshold: 2.0
  exit_threshold: 0.5
  blowout_threshold: 3.0
beta:
  method: ols_rolling
  lookback_bars: 60
sizing:
  allocation_pct_nav: 5.0
  beta_neutral: true
take_profit_logic:
  tp_logic: zscore_meanrev
  tp_logic_params: {threshold: 0.5}
stop_loss_logic:
  sl_logic: zscore_blowout
  sl_logic_params: {threshold: 3.0}
risk:
  max_pairs_concurrent: 1
  entry_lockout_post_sl_minutes: 30
  max_hold_duration_minutes: 90
enabled_in_modes: [AGGRESSIVE]
```

---

## Pièce F — tests (à écrire avec chaque phase D)

**Niveau 1 — unitaires métier** (15+ tests minimum) :
- `test_cointegration_detects_known_coint` (synthetic stationary residuals → PASS)
- `test_cointegration_rejects_random_walks` (2 RW indépendants → FAIL)
- `test_zscore_computation_correct` (vs numpy reference)
- `test_beta_ols_correct` (vs sklearn reference)
- `test_pair_sizing_beta_neutral` (assert sum_dollars(legs) ≈ 0 in market-direction)
- `test_pair_tracker_state_transitions` (IDLE→ARMED_LONG→IN_TRADE→TP_HIT→LOCKOUT)
- `test_pair_tracker_blowout_sl` (z monte au-delà de 3.0 → SL)
- `test_pair_tracker_time_stop` (z stagne 18 bars sans TP → time-stop)
- `test_pair_tracker_lockout_post_sl` (entry refusée 30 min post-SL)
- `test_pair_tracker_no_double_arm` (z déjà au-delà de seuil, pas de re-armement)
- `test_simultaneous_dual_leg_open_atomic` (mock ExecutionEngine — soit 2 fills soit 0)
- `test_simultaneous_dual_leg_close_on_tp` (TP hit → close 2 legs)
- `test_zscore_sl_resolver` + `test_zscore_tp_resolver`
- `test_journal_pair_fields_populated`
- `test_max_pairs_concurrent_enforced`

**Niveau 2 — intégration moteur** :
- Chargement YAML.
- Mapping loader OK.
- Setup généré sur fixture contrôlée 5m × 100 bars synthétiques (SPY+QQQ avec spread injectée).
- Zéro régression sur suite existante (33/33 engine sanity, etc.).

---

## Pièce G — protocole de run

| Champ | Valeur |
|---|---|
| Smoke week canon | nov_w4 (2025-11-17 → 2025-11-21), 5 sessions NY |
| 4 semaines validation | jun_w3 + aug_w3 + oct_w2 + nov_w4 (post-smoke PASS uniquement) |
| Mode | AGGRESSIVE, IdealFillModel d'abord (smoke), `--realistic` si smoke PASS pour 4w |
| Allowlist | `Stat_Arb_SPY_QQQ_v1` seul |
| Caps | actives + kill-switch actif |
| Artefacts | manifest + summary + trades parquet + verdict §18.3 5 blocs |

---

## Pièce H — kill rules pré-écrites (avant smoke, non re-interprétables post-hoc)

**Smoke nov_w4 — KILL si une seule de ces conditions tient :**

| Rule | Threshold | Action si violé |
|---|---|---|
| `n` (setups émis) | < 10 sur 5 sessions | KILL → SMOKE_FAIL → ARCHIVED. Cas A ou B §20 selon audit infra. |
| `mean_reversion_rate` (z atteint exit_threshold avant SL/time-stop) | < 50 % | KILL → SMOKE_FAIL → ARCHIVED. Cas C §20 (signal absent). |
| `E[R] gross` | ≤ 0 | KILL → SMOKE_FAIL → ARCHIVED. |

**Si smoke PASS (n ≥ 10 ET mean_rev_rate ≥ 50% ET E[R] gross > 0)** :
- Promotion automatique vers 4-semaines validation.
- Bar promotion final (per §10) : `E[R] net+slippage > 0.10R + n > 30 + PF > 1.2 + gates O5.3 PASS`.

**Pas de tuning post-smoke** dans la phase D6. Si smoke FAIL avec n suffisant mais E[R] borderline, classer Cas C et ARCHIVED. Une nouvelle hypothèse (nouveaux seuils, autre paire, autre lookback) requiert un **nouveau dossier v2** — pas un patch v1 (§10 règle "Réouverture branche morte").

---

## Décision d'engagement

Ce dossier place `Stat_Arb_SPY_QQQ_v1` au statut `SPECIFIED_BLOCKED_BY_INFRA`. Le passage à `IMPLEMENTED` requiert le chantier infra complet (5 phases D1–D6, ~5 jours).

**Bloquant majeur** : la primitive `simultaneous_dual_leg_open` touche `ExecutionEngine` qui est validé byte-identique Phase W. Tout changement doit préserver cette propriété pour les playbooks single-leg existants. Stratégie : ajouter une méthode `open_pair_atomic` **sans modifier** `open_position` (rétrocompat stricte).

**Décision utilisateur explicite requise** avant lancement phase D1 (commitment 5 jours).

---

## 2026-04-22 — Statut post-smoke : `SMOKE_FAIL → ARCHIVED`

Phases exécutées (D3 contourné par un harness autonome pour obtenir un verdict sans toucher `ExecutionEngine`) :

- **D1** — helpers purs ([zscore](../../../engines/stat_arb/zscore.py), [cointegration](../../../engines/stat_arb/cointegration.py), [sizing](../../../engines/stat_arb/sizing.py)) + 20 tests PASS.
- **D2** — [PairSpreadTracker](../../../engines/stat_arb/tracker.py) + 11 tests PASS.
- **D3'** — [harness autonome](../../../scripts/stat_arb_smoke.py) (contourne `ExecutionEngine` pour obtenir verdict avant commitment infra complet).
- **D6** — smoke nov_w4 exécuté.

**Résultat smoke** : n=8, WR=37.5 %, E[R] gross=−0.179, PF=0.258, peak_R p80=0.15, mean_rev_rate=25 %. **Kill rules pré-écrites §H atteintes 3/3** (n<10, mean_rev<50%, E[R]≤0).

**Cas §20** : C (edge absent) + secondaire B (gate cointégration EG strict intraday trop restrictif). Les 2 TP mean-reversion produisent les pires pertes (−0.47R, −0.94R) → le chemin prix entre armement et exit z=0.5 comporte des excursions adverses dépassant le retour à la moyenne.

**Verdict complet** : [stat_arb_spy_qqq_v1_smoke_nov_w4_verdict.md](../../../data/backtest_results/stat_arb_spy_qqq_v1_smoke_nov_w4_verdict.md)

**Statut final** : `ARCHIVED`. Hypothèse SPY-QQQ 5m intraday mean-reverting **réfutée** pour la configuration testée. Briques D1+D2 (31 tests PASS) **préservées** et réutilisables pour toute future tentative stat-arb (paire alternative, TF daily cointégration, régime VIX gate).
