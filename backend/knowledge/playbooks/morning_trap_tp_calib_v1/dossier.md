# Morning_Trap_Reversal — TP peak-R calibration v1 (Leg 1.2)

Dossier §18 — 8 pièces obligatoires avant run.
Statut initial : `SPECIFIED_READY` (infra full existe, c'est une calibration YAML-only, pas un nouveau playbook).

**Note budget §19.3** : itération **4/3 exceptionnelle terminale** — CLAUDE.md user-marked "1 dernier levier TP peak-R calibrated avant KILL" suite au cumul B1→B2→C.1→M (-0.147 → -0.123 → -0.081 → +0.003 gross M / -0.062 net). Si ARCHIVED → **KILL définitif Morning_Trap_Reversal**, aucune nouvelle tentative.

---

## Pièce A — fiche d'identité

- **Nom canonique** : `Morning_Trap_Reversal` (playbook existant, non renommé)
- **Campagne** : `morning_trap_tp_calib_v1` (override YAML dédiée)
- **Version** : v1 calibration (itération 4/3 exceptionnelle terminale §19.3)
- **Famille** : vocab-borrowing ICT — reversal pattern sur false breakout NY 09:30-10:30 ET (pas MASTER-faithful D/4H bias)
- **Type** : stateless instant (détection 5m candlestick + sweep + vwap_regime gate)
- **Instruments** : SPY, QQQ
- **Timeframes** : setup 5m, execution 5m (confirmation_tf déclaré 1m mais pas gate actif)
- **Direction** : contrarian (hammer/engulfing/morning_star SHORT vs rejet haussier ; shooting_star/evening_star LONG vs rejet baissier)
- **Régime visé** : NY RTH 09:30-10:30 ET (première heure, max 2 setups/session)
- **Statut initial** : `SPECIFIED_READY` (override YAML d'un playbook `DENYLIST + IMPROVE candidat`)
- **Origine de l'idée** : §0.5 arbre Leg 1.2 — levier TP peak-R jamais tenté sur Morning_Trap après 3 itérations consommées (B2 BE patch, C.1 vwap_regime, M baseline). peak_R p60=0.827R vs TP1 3.0R actuel = unreachable par design.
- **Date** : 2026-04-22

---

## Pièce B — hypothèse formelle

### Thèse
Le signal Morning_Trap 5m produit des excursions favorables moyennes de 0.83R (p60 peak_R sur survivor_v1 corpus) et un tail expansif (p80=2.43R, audit peakR_vs_TP). Un TP1 calibré à ~p60 (0.83R) capture la majorité des winners qui actuellement expirent via TP1 3.0R unreachable (hit rate baseline 8%), en acceptant un RR 0.83:1 (WR min break-even = 54.7%).

### Mécanisme
Morning_Trap = rejet d'un faux breakout dans la première heure NY (après swing HTF night session). Le rejet initial est net (pattern reversal + vwap_regime gate) mais le follow-through est borné par la structure intraday — le marché retourne vers le VWAP / mid-range avant d'aller chercher un niveau de liquidité plus lointain. Résultat : peak_R structurellement plafonné ~1-2R médian, tail expansif mais rare. Fixed RR 3.0R rate systématiquement (8% hit baseline).

### Conditions de fertilité
- Première heure NY RTH (volume + volatilité maximale, rejets 5m significatifs)
- vwap_regime aligné (gate déjà actif C.1 patch, +0.042 E[R] vs unfiltered)
- Régime vol fertile (VIX 15-25) où rejets intraday ont suite
- Direction contrarian au pattern (shooting_star SHORT etc. = rejet directionnel)
- max_setups_per_session = 2 (cap binding observé C.1, sélection top-2 patterns/jour)

### Conditions de stérilité
- Vol panique (VIX>25) : rejets deviennent noise, pas signal
- Low-vol (VIX<15) : pas assez d'amplitude pour atteindre même 0.83R
- Uptrend fort + pattern contrarian LONG-biased : rejets baissiers = correction rapide qui dépasse SL
- Trend continuation (pas vraiment "trap") : pattern vocab match mais contexte exige continuation, pas reversal

### Risque principal (falsifiabilité)
Si WR < 54.7 % avec TP1=0.83R sur 4w canonical, l'hypothèse est réfutée — le signal n'a pas assez de winners pour compenser le RR défavorable, même en capturant p60 peak_R. **Baseline survivor_v1 Morning_Trap WR = 16 %** (n=25) et **M baseline WR = 26 %** (n=34) — le gap jusqu'à 54.7 % est énorme. Hypothèse réaliste : cette calibration améliore E[R] sans croiser zéro, confirmant que **le signal Morning_Trap est structurellement incapable de WR cohérent** quel que soit le TP — et donc **KILL définitif** per CLAUDE.md user-marked.

Corollaire : si E[R]_net ≤ 0 sur 4w canonical, Morning_Trap rejoint le cimetière des signaux vocab-borrowing ICT sans edge (0/7 Phase D.2 MASTER faithful audit + Engulfing_Bar_V056 Leg 1.1 ARCHIVED 2026-04-22).

---

## Pièce C — spécification d'état décisionnel

**Stateless** (pas de state machine).

- **Point d'armement** : N/A (instant trigger)
- **Point de confirmation** : candlestick pattern détecté sur 5m (shooting_star / hammer / engulfing / evening_star / morning_star) + `require_sweep: true` sur 5m + `vwap_regime: true` gate (C.1 patch)
- **Point d'émission setup** : bar close confirme pattern + sweep + vwap aligné, entry LIMIT @ pattern_close next bar
- **Point d'invalidation** : N/A (stateless, un rejet = une opportunité évaluée immédiatement)
- **Timeouts** : `max_duration_minutes: 120` (réduit de 155 B2 patch — cohérent TP serré, capture TP1 sinon exit)

---

## Pièce D — dépendances moteur + audit infra

### Détecteurs requis
- Candlestick detectors (shooting_star, hammer, engulfing, evening_star, morning_star) — **EXISTE** ([backend/engines/patterns/](backend/engines/patterns/)), audit sanity_v2 PASS (test B3 engulfing 1:1)
- `detect_liquidity_sweep` — **EXISTE**, audit sanity_v2 PASS

### Trackers requis
- Aucun (stateless)

### Helpers géométriques
- vwap_regime gate — **EXISTE** (C.1 patch, [setup_engine_v2.py](backend/engines/setup_engine_v2.py))

### Logique de session
- NY RTH 09:30-10:30 ET — **EXISTE** (time_windows playbook actuel, ET strict post-Sprint 1 timezone audit)

### SL logic
- `type: SWING`, `distance: trap_extreme`, `padding_ticks: 1` — **EXISTE**

### TP logic
- Fixed RR (`tp1_rr`, `tp2_rr`) — **EXISTE** (schéma legacy, pas `liquidity_draw` α'')
- Trailing ratchet + breakeven — **EXISTE**, audit sanity_v2 PASS (A4, A11)

### Risk hooks
- ALLOWLIST/DENYLIST, caps session (max_setups_per_session=2), cooldown 5min — **EXISTE** ([risk_engine.py](backend/engines/risk_engine.py))
- `DENYLIST` actuel ([modes.yml:53](backend/knowledge/modes.yml)) → **bypass requis via CALIB_ALLOWLIST** (pattern Leg 1.1 Engulfing reproduit : `RISK_EVAL_ALLOW_ALL_PLAYBOOKS=true` + `--calib-allowlist Morning_Trap_Reversal`)

### Champs runtime journal
- `tp_reason`, `exit_reason` — **EXISTE**

### Résultat audit infra
**`full infra exists`** → statut peut passer directement `IMPLEMENTED` via override YAML. Aucun chantier code requis.

---

## Pièce E — YAML d'exécution

Fichier : [backend/knowledge/campaigns/morning_trap_tp_calib_v1.yml](backend/knowledge/campaigns/morning_trap_tp_calib_v1.yml)

Override complet du playbook `Morning_Trap_Reversal` avec :
- **TP1 3.0R → 0.83R** (calibré sur peak_R p60 = 0.827R audit peakR_vs_TP survivor_v1)
- **TP2 5.0R → 1.50R** (ratio conservé, capture tail entre p60 et p80=2.43R)
- **breakeven_at_rr 2.15 → 0.40R** (protection winners qui touchent p50=0.448R mais reviennent)
- **trailing_trigger_rr null → 0.50R** (ratchet ajouté cohérent TP serré)
- **trailing_offset_rr null → 0.25R**
- **min_rr 3.0 → 0.83R** (gate mise à jour cohérent TP1)
- **max_duration_minutes 155 → 120** (cohérent TP serré, capture TP1 ou exit)
- Tous les autres champs identiques (vwap_regime, require_sweep, candlestick_patterns, time_range 09:30-10:30, max_setups_per_session=2)

Flag verdict : **LARGE_TP1_CUT** (TP1 coupé de 72%, effet structural majeur sur distribution exit_reason).

---

## Pièce F — tests

**Niveau 1 (unitaires)** : non requis — override de paramètres YAML d'un playbook déjà testé. `Morning_Trap_Reversal` passe déjà suite de tests existante (candlestick detectors, liquidity_sweep, SL/TP fixed, breakeven, trailing — cf engine_sanity_v2 33/33).

**Niveau 2 (intégration)** :
- Smoke test chargement YAML : `morning_trap_tp_calib_v1.yml` load sans erreur, `tp1_rr=0.83` visible dans resolved config
- 4w canonical direct (pas de smoke 1w isolé — pattern Leg 1.1 Engulfing : calibration YAML triviale, infra ultra-rodée)

---

## Pièce G — protocole de run

- **Mode** : `backtest` avec caps actives (ALLOWLIST/cooldown/session_cap) — pattern Leg 1.1 Engulfing
- **Fill model** : IdealFillModel (backtest default) — commission_model=ibkr_fixed, slippage_pct=0.05%, spread_bps=2.0 (config `run_mini_lab_week`). Reconcile slippage post-hoc via reconcile_paper_backtest si gate Stage 1 PASS.
- **Allowlist** : `Morning_Trap_Reversal` seul (aucun autre playbook actif — isolation edge per §5.4)
- **Mode exec** : `RISK_EVAL_ALLOW_ALL_PLAYBOOKS=true` + `RISK_EVAL_CALIB_ALLOWLIST=Morning_Trap_Reversal` (bypass DENYLIST pour calibration)
- **4 semaines canoniques** : jun_w3 (2025-06-16→06-20) + aug_w3 (2025-08-18→08-22) + oct_w2 (2025-10-06→10-10) + nov_w4 (2025-11-17→11-21)
- **Corpus** : local parquet, SPY+QQQ 1m
- **Artefacts** : manifest.json + summary.json + trades.parquet + verdict §18.3 structuré

### Commande canonique
```bash
cd backend && .venv/bin/python scripts/run_mini_lab_week.py \
  --weeks jun_w3 aug_w3 oct_w2 nov_w4 \
  --label morning_trap_tp_calib_v1_4w \
  --output-parent morning_trap_tp_calib \
  --no-respect-allowlists \
  --no-relax-caps \
  --calib-allowlist Morning_Trap_Reversal \
  --playbooks-yaml knowledge/campaigns/morning_trap_tp_calib_v1.yml
```

---

## Pièce H — kill rules pré-écrites (obligatoires avant run, §18.4)

### Règles d'archivage TERMINAL (KILL définitif Morning_Trap_Reversal)
**Si UNE des conditions suivantes est vraie après 4w canonical, le playbook est KILL terminal et l'arbre §0.5 progresse vers Leg 2 sans itération supplémentaire :**

1. `E[R]_net ≤ 0` (signal ne croise pas zéro même avec TP peak-R calibré — 4 itérations consommées)
2. `WR < 40 %` (distribution winners trop faible pour RR 0.83:1 soutenable)
3. `PF < 1.0` (gross_profit < gross_loss, perte algébrique certaine à long terme)

**Conformément à CLAUDE.md user-marked "1 dernier levier TP peak-R calibrated avant KILL"** — si UNE kill rule est atteinte, aucune nouvelle tentative sans hypothèse structurellement nouvelle (§10 réouverture branche morte interdite).

### Gate passage Stage 1 (Validate Edge, §0.6)
**Pour passer à Stage 2 (Amplify R), TOUTES les conditions suivantes doivent être vraies :**

1. `E[R]_net > 0.05R` gross (signe de vie minimal per §0.5 Leg 1.1)
2. `n ≥ 15` trades (signal exercé, pas fluke)
3. `peak_R p60 > 0.5R` (excursion conservée post-calib, pas juste fluke winners serrés)
4. **Split régime §0.4-bis obligatoire** dans verdict : E[R] par régime session × vol × trend — pas d'edge "universel" si 1 régime porte tout (exigence cross-regime §0.6 Stage 1)
5. `0 weeks < -0.5R` per-week (pas de drawdown catastrophique isolé)

### Décision intermédiaire (ni KILL ni passage Stage 1)
**IMPOSSIBLE pour Morning_Trap** — itération 4/3 exceptionnelle terminale. Pas de sous-cas B (§20). Soit KILL définitif, soit Stage 1 PASS (improbable vu baseline WR 16-26 %).

### Budget d'itération §19.3
Cette calibration compte comme **itération 4/3 exceptionnelle terminale** du budget post-smoke Morning_Trap_Reversal.
- Déjà tenté : B1 review (Morning_Trap flagged CALIBRATE) + B2 BE patch (E[R] -0.147 → -0.123) + C.1 vwap_regime (-0.123 → -0.081) + M baseline (+0.003 gross / -0.062 net)
- Calibration actuelle : 4/3 (exception CLAUDE.md user-marked)
- **Si ARCHIVED, terminal** — aucune nouvelle tentative sans hypothèse structurellement nouvelle (§10 + §19.3).
