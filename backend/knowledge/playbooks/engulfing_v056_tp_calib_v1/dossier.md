# Engulfing_Bar_V056 — TP peak-R calibration v1 (Leg 1.1)

Dossier §18 — 8 pièces obligatoires avant code/YAML.
Statut initial : `SPECIFIED_READY` (infra full existe, c'est une calibration YAML-only, pas un nouveau playbook).

---

## Pièce A — fiche d'identité

- **Nom canonique** : `Engulfing_Bar_V056` (playbook existant, non renommé)
- **Campagne** : `engulfing_v056_tp_calib_v1` (override YAML dédiée)
- **Version** : v1 calibration (itération 1/3 budget §19.3)
- **Famille** : ICT-adjacent vocab — candlestick reversal (pas MASTER-faithful D/4H bias)
- **Type** : stateless instant (détection 1 bar 5m, TP/SL calibrés)
- **Instruments** : SPY, QQQ
- **Timeframes** : setup 5m, execution 5m
- **Direction** : any (audit filter_splits révèle edge potentiel sur SHORT only — à observer dans verdict)
- **Régime visé** : NY session 09:30-12:00 + 14:00-15:30 ET (fenêtres existantes playbook)
- **Statut initial** : `SPECIFIED_READY` (override YAML d'un playbook `IMPLEMENTED`)
- **Origine de l'idée** : §0.5 arbre Leg 1.1 — levier TP peak-R jamais tenté sur Engulfing (peak_R p60=0.663R vs TP1=2.0R actuel = unreachable par design)
- **Date** : 2026-04-22

---

## Pièce B — hypothèse formelle

### Thèse
Le signal Engulfing 5m produit des excursions favorables moyennes de 0.66R (p60 peak_R sur survivor_v1 corpus). Un TP1 calibré à ~p60 (0.68R) capture les winners qui expirent actuellement via time_stop ou retournent BE → SL, en acceptant un RR 0.68:1 (WR min break-even = 59.5%).

### Mécanisme
Engulfing bar = rejet directionnel fort (close opposé couvrant prior range H/L). Mais sans HTF bias / liquidity target, l'excursion est bornée : le marché ne va pas "chercher" un niveau structurel particulier — il oscille autour du rejet. Résultat : peak_R structurellement plafonné ~1R. Fixed RR 2.0R rate systématiquement.

### Conditions de fertilité
- Session NY RTH (volume suffisant pour que rejet 5m soit significatif)
- Régime vol fertile (VIX 15-25) où rejets intraday ont suite
- Direction favorable au contexte : audit filter_splits montre SHORT +0.063 E[R] / LONG négatif sur survivor_v1 — possible asymétrie régime uptrend 2025 (rejets haussiers dans uptrend = continuation ; rejets baissiers = correction rapide). **À vérifier** sur 4w canonical.

### Conditions de stérilité
- Vol panique (VIX>25) : rejets deviennent noise, pas signal
- Low-vol (VIX<15) : pas assez d'amplitude pour atteindre même 0.68R
- Overnight/gap days : engulfing bar au open 5m = artefact gap, pas rejet structurel

### Risque principal (falsifiabilité)
Si WR < 59.5 % avec TP1=0.68R, l'hypothèse est réfutée — le signal n'a pas assez de winners pour compenser le RR défavorable, même en capturant p60 peak_R. Corollaire : si E[R]_net ≤ 0 sur 4w canonical malgré la calibration, Engulfing rejoint le cimetière des signaux vocab-borrowing ICT sans edge (0/7 Phase D.2 MASTER faithful audit).

---

## Pièce C — spécification d'état décisionnel

**Stateless** (pas de state machine).

- **Point d'armement** : N/A (instant trigger)
- **Point de confirmation** : candlestick pattern `engulfing` détecté sur 5m par moteur existant (`detect_engulfing`)
- **Point d'émission setup** : bar close confirme pattern, entry MARKET @ pattern_close next bar
- **Point d'invalidation** : N/A (stateless, un rejet = une opportunité évaluée immédiatement)
- **Timeouts** : `max_duration_minutes: 120` (conservé playbook existant)

---

## Pièce D — dépendances moteur + audit infra

### Détecteurs requis
- `detect_engulfing` — **EXISTE** ([backend/engines/patterns/](backend/engines/patterns/)), audit sanity_v2 PASS (test B3 engulfing 1:1)

### Trackers requis
- Aucun (stateless)

### Helpers géométriques
- Aucun

### Logique de session
- NY session 09:30-12:00 + 14:00-15:30 ET — **EXISTE** (time_windows playbook actuel, ET strict post-Sprint 1 timezone audit)

### SL logic
- `type: FIXED`, `distance: pattern_extreme`, `padding_ticks: 1` — **EXISTE**

### TP logic
- Fixed RR (`tp1_rr`, `tp2_rr`) — **EXISTE** (schéma legacy, pas `liquidity_draw` α'')
- Trailing ratchet + breakeven — **EXISTE**, audit sanity_v2 PASS (A4, A11)

### Risk hooks
- ALLOWLIST/DENYLIST, caps session, cooldown 5min — **EXISTE** ([risk_engine.py](backend/engines/risk_engine.py))

### Champs runtime journal
- `tp_reason`, `exit_reason` — **EXISTE**

### Résultat audit infra
**`full infra exists`** → statut peut passer directement `IMPLEMENTED` via override YAML. Aucun chantier code requis.

---

## Pièce E — YAML d'exécution

Fichier : [backend/knowledge/campaigns/engulfing_v056_tp_calib_v1.yml](backend/knowledge/campaigns/engulfing_v056_tp_calib_v1.yml)

Override complet du playbook `Engulfing_Bar_V056` avec :
- **TP1 2.0R → 0.68R** (calibré sur peak_R p60 = 0.663R audit peakR_vs_TP)
- **TP2 4.0R → 1.20R** (conservé proportionnel, capture tail p80=1.07R)
- **breakeven_at_rr 1.0 → 0.40R** (protection winners qui touchent p50=0.276R mais reviennent)
- **trailing_trigger_rr 1.0 → 0.50R** (ratchet plus agressif cohérent TP serré)
- **trailing_offset_rr 0.5 → 0.25R**
- **min_rr 2.0 → 0.68R** (gate mise à jour)
- Tous les autres champs identiques (`playbooks.yml:1258`)

Flag verdict : **LARGE_TP1_CUT** (TP1 coupé de 66%, effet structural majeur sur distribution exit_reason).

---

## Pièce F — tests

**Niveau 1 (unitaires)** : non requis — override de paramètres YAML d'un playbook déjà testé. `Engulfing_Bar_V056` passe déjà suite de tests existante (detect_engulfing, SL/TP fixed, breakeven, trailing — cf engine_sanity_v2 33/33).

**Niveau 2 (intégration)** :
- Smoke test chargement YAML : `campaign_engulfing_v056_tp_calib_v1.yml` load sans erreur, `tp1_rr=0.68` visible dans resolved config
- Smoke test 1 semaine (nov_w4) avant 4w canonical pour vérifier absence de régression détecteur

---

## Pièce G — protocole de run

- **Mode** : `backtest` avec caps actives (ALLOWLIST/cooldown/session_cap)
- **Fill model** : **ConservativeFillModel** obligatoire (§0.2 non-négociable #6 pour promotion — même si §0.7 pas encore câblé par défaut, passer via flag si dispo sinon IdealFillModel + reconcile slippage post-hoc)
- **Allowlist** : `Engulfing_Bar_V056` seul (aucun autre playbook actif — isolation edge per §5.4)
- **4 semaines canoniques** : jun_w3 (2025-06-16→06-20) + aug_w3 (2025-08-18→08-22) + oct_w2 (2025-10-06→10-10) + nov_w4 (2025-11-17→11-21)
- **Corpus** : local parquet, SPY+QQQ 1m
- **Artefacts** : manifest.json + summary.json + trades.parquet + verdict §18.3 structuré

### Commande canonique
```bash
cd backend && .venv/bin/python scripts/run_mini_lab_week.py \
  --weeks jun_w3 aug_w3 oct_w2 nov_w4 \
  --label engulfing_v056_tp_calib_v1_4w \
  --output-parent engulfing_v056_tp_calib \
  --calib-allowlist Engulfing_Bar_V056 \
  --playbooks-yaml knowledge/campaigns/engulfing_v056_tp_calib_v1.yml
```

---

## Pièce H — kill rules pré-écrites (obligatoires avant smoke, §18.4)

### Règles d'archivage immédiat (ARCHIVED → node 1.2 Morning_Trap)
**Si UNE des conditions suivantes est vraie après 4w canonical, le playbook est ARCHIVED et l'arbre §0.5 progresse vers node 1.2 sans itération supplémentaire :**

1. `E[R]_net ≤ 0` (signal ne croise pas zéro même avec TP peak-R calibré)
2. `WR < 40 %` (distribution winners trop faible pour RR 0.68:1 soutenable)
3. `PF < 1.0` (gross_profit < gross_loss, perte algébrique certaine à long terme)

### Gate passage Stage 1 (Validate Edge, §0.6)
**Pour passer à Stage 2 (Amplify R), TOUTES les conditions suivantes doivent être vraies :**

1. `E[R]_net > 0.05R` gross (signe de vie minimal per §0.5 Leg 1.1)
2. `n ≥ 15` trades (signal exercé, pas fluke)
3. `peak_R p60 > 0.5R` (excursion conservée post-calib, pas juste fluke winners serrés)
4. **Split régime §0.4-bis obligatoire** dans verdict : E[R] par régime session × vol × trend — pas d'edge "universel" si 1 régime porte tout (exigence cross-regime §0.6 Stage 1)
5. `0 weeks < -0.5R` per-week (pas de drawdown catastrophique isolé)

### Décision intermédiaire (ni ARCHIVED ni passage Stage 1)
Si `E[R]_net > 0` mais gate Stage 1 pas atteint (n < 15 OU peak_R p60 ≤ 0.5R OU 1 régime domine), décision **§20 Cas B (sous-exercé)** :
- max 1 itération ciblée (ex: élargir time_windows ou tester `direction: short` only si asymétrie confirmée)
- si 2e FAIL → ARCHIVED, node 1.2

### Budget d'itération §19.3
Cette calibration compte comme **itération 1/3** du budget post-smoke Engulfing_Bar_V056.
- Déjà tenté : v1 natif Phase 5a (status ALLOWLIST) + audit peakR_vs_TP observation
- Calibration actuelle : 1/3
- Si ARCHIVED, aucune nouvelle tentative sans hypothèse structurellement nouvelle (§10)
