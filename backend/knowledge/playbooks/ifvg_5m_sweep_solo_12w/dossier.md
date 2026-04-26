# Dossier — IFVG_5m_Sweep solo 12w (Leg 2.1 Quarantine PROMOTE)

**Source** : CEO arbre §0.5 Leg 2 — candidats CLAUDE.md "quarantine" E[R]>0 sur n=3-11 : **besoin data, pas calibration**.

---

## Pièce A — fiche d'identité

| Champ | Valeur |
|---|---|
| Nom canonique | IFVG_5m_Sweep (baseline playbooks.yml L750) |
| Version solo-run | 12w corpus expansion v1 |
| Famille | MASTER Aplus_01/03 (IFVG 5m après sweep de liquidité, entrée 1m dans zone IFVG) |
| Type | Stateless 5m detector + 1m confirmation (no tracker) |
| Instruments | SPY, QQQ |
| Timeframes | 5m setup + 1m confirmation |
| Direction | both (contrarian candlestick) |
| Régime visé | trend + manipulation_reversal, htf_bias bullish/bearish allowed |
| Statut initial | quarantine (CLAUDE.md — E[R]>0 sur n=3-11 à valider sur corpus élargi) |
| Auteur | baseline playbook v0 (MASTER Family A transcripts) |
| Dernière review | 2026-04-22 (Leg 2.1 démarrage) |

---

## Pièce B — hypothèse formelle

### Thèse
Sur un setup IFVG 5m (inverse FVG = zone FVG qui a été invalidée et testée en resistance/support opposé) post-sweep de liquidité, l'entrée 1m contrarian dans la zone IFVG capture un mean-reversion statistiquement probable quand le price rejette la zone avec un pattern bougie (engulfing/pin/hammer/shooting_star/marubozu).

### Mécanisme
Le sweep de liquidité draine les stops (liquidity grab). L'IFVG agit alors comme zone de résistance institutionnelle où le smart money prend position en direction opposée au sweep. Le 1m confirmation filter réduit le faux-rejet (entrée précoce).

### Conditions de fertilité
- Session NY 09:30-15:00 (liquidité principale)
- htf_bias bullish OU bearish (éviter range)
- ADX ≥ 20 (structure directionnelle minimale)
- day_type trend OU manipulation_reversal (cf SharedContext)

### Conditions de stérilité
- Range pur (ADX < 20)
- Session lunch (12:00-13:30) — bruit liquidité insuffisante
- Day manipulation_absorption (stable, pas de sweep)

### Risque principal (falsifiabilité)
Si **E[R]_gross ≤ 0 sur n ≥ 20 trades 12 weeks**, l'hypothèse est réfutée : le signal IFVG 5m + sweep + contrarian pattern + 1m confirm ne capture pas d'edge en 2025. Corroboré si cohort Aplus_03 R.3 (R.3 E[R]=-0.055 n=35) s'aggrave en élargi.

---

## Pièce C — spécification d'état décisionnel

**Stateless** (pas de tracker) — fonctionnement au tick-by-tick :

1. **Détection setup (5m)** : bar 5m fermée ET price dans zone IFVG active ET candlestick pattern `required_families` détecté ET direction `contrarian`.
2. **Gate context (scorer)** : htf_bias allowed + day_type allowed + structure_htf cohérent + ADX ≥ 20.
3. **Entry 1m** : LIMIT order à `pattern_close`, confirmation_tf=1m.
4. **SL swing** : recent_swing ± 2 ticks.
5. **TP liquidity draw** : fixed RR 3.0/5.0 (baseline YAML — PAS d'override dans solo-run 12w).
6. **Invalidation** : SL touché OR max_duration_minutes=45 OR EOD.

---

## Pièce D — dépendances moteur + audit infra

| Brique | Status | Fichier |
|---|---|---|
| IFVG detector | ✓ validé (engine sanity v2 B2) | [backend/engines/patterns/ifvg.py](backend/engines/patterns/ifvg.py) |
| Sweep detector | ✓ validé (engine sanity v2 B3) | [backend/engines/patterns/sweep.py](backend/engines/patterns/sweep.py) |
| Candlestick patterns | ✓ (engine sanity v2 B2b) | [backend/engines/patterns/candlestick.py](backend/engines/patterns/candlestick.py) |
| 1m confirmation gate | ✓ | [backend/engines/execution/entry_gates.py](backend/engines/execution/entry_gates.py) |
| Swing SL logic | ✓ (engine sanity v2 A1/A2) | [backend/engines/execution/stop_loss.py](backend/engines/execution/stop_loss.py) |
| Fixed RR TP | ✓ | [backend/engines/execution/take_profit.py](backend/engines/execution/take_profit.py) |
| Context requirements (ADX, htf_bias) | ✓ | [backend/engines/setup_engine_v2.py](backend/engines/setup_engine_v2.py) |
| TimeframeAggregator 5m/1m | ✓ (engine sanity v1 after gap-merge fix) | [backend/engines/timeframe_aggregator.py](backend/engines/timeframe_aggregator.py) |

**Résultat audit** : `full infra exists` — aucun chantier requis. Baseline YAML playbooks.yml L750 exécutable tel quel.

---

## Pièce E — YAML d'exécution

- **Approche solo-run** : pas d'override YAML spécifique. On utilise le playbook `IFVG_5m_Sweep` **as-is** (baseline playbooks.yml L750) avec `RISK_EVAL_CALIB_ALLOWLIST=IFVG_5m_Sweep` pour isoler le playbook (pas de cross-contamination).
- **Pas de TP peak-R calib** : per plan §0.5 Leg 2, "besoin data, pas calibration" → TP/SL baseline inchangés. Calibration éventuelle vient si WF_PASS + promotion vers Stage 2.
- **Caps actives** : `--no-relax-caps` (cooldown 5min, session_cap max_setups_per_session=2, kill-switch par défaut).

---

## Pièce F — tests

Aucun test dédié nécessaire pour le solo-run (baseline playbook déjà testé). Les briques moteur sous-jacentes ont 33/33 tests PASS (engine_sanity v1 + v2) + 4/4 audits engine honesty.

---

## Pièce G — protocole de run

### Corpus 12 semaines (jun-nov 2025 étendu)

Sélection cross-regime §0.4-bis pour couvrir sessions × vol × trend × day-of-week :

| Semaine | Label | Start | End |
|---|---|---|---|
| 1 | jun_w2 | 2025-06-09 | 2025-06-13 |
| 2 | jun_w3 (canonical) | 2025-06-16 | 2025-06-20 |
| 3 | jul_w2 | 2025-07-07 | 2025-07-11 |
| 4 | jul_w4 | 2025-07-21 | 2025-07-25 |
| 5 | aug_w1 | 2025-08-04 | 2025-08-08 |
| 6 | aug_w3 (canonical) | 2025-08-18 | 2025-08-22 |
| 7 | sep_w2 | 2025-09-08 | 2025-09-12 |
| 8 | sep_w4 | 2025-09-22 | 2025-09-26 |
| 9 | oct_w1 | 2025-09-29 | 2025-10-03 |
| 10 | oct_w2 (canonical) | 2025-10-06 | 2025-10-10 |
| 11 | nov_w2 | 2025-11-03 | 2025-11-07 |
| 12 | nov_w4 (canonical) | 2025-11-17 | 2025-11-21 |

Inclut 4 semaines canoniques + 8 semaines d'extension corpus.

### Mode de run
- Mode : AGGRESSIVE avec `RISK_EVAL_ALLOW_ALL_PLAYBOOKS=true RISK_EVAL_CALIB_ALLOWLIST=IFVG_5m_Sweep` (bypass DENYLIST + isole solo)
- Caps actives : `--no-relax-caps`
- Fill model : Ideal (baseline — slippage budget -0.065R/trade noté pour WF_PASS éventuel)
- Manifest + summary + trades parquet + verdict écrits

### Commande canonique par semaine
```bash
cd backend && .venv/bin/python scripts/run_mini_lab_week.py \
  --start <YYYY-MM-DD> --end <YYYY-MM-DD> \
  --label ifvg_5m_sweep_solo_12w_<week_label> \
  --output-parent ifvg_5m_sweep_solo_12w \
  --no-respect-allowlists --no-relax-caps \
  --calib-allowlist IFVG_5m_Sweep
```

---

## Pièce H — kill rules pré-écrites (AVANT smoke)

### Gate Leg 2 cohort (plan §0.5)
> Kill rule cohort : si 0/3 passe **E[R] > 0.05R gross + n ≥ 20** → Leg 3

### Kill rules individuelles IFVG_5m_Sweep 12w
1. **n < 20 trades sur 12 semaines** → **ARCHIVED** (signal structurellement rare, non-calibrable)
2. **E[R]_gross ≤ 0** → **ARCHIVED** (edge absent, Cas §20 C)
3. **E[R]_gross ∈ [0, +0.05R] ET n ≥ 20** → **MARGINAL, pas promotion Stage 1** (rejected per user bar feedback_real_results_bar.md +0.02R minimum, +0.10R promotion)
4. **E[R]_gross > 0.05R ET n ≥ 20** → **PASS Leg 2 criterion** → candidat max(E[R]_gross parmi 3) avance vers Stage 1 refactor α'' + 4w canonical

### Décision terminale
- 2+ kill rules atteintes → ARCHIVED terminal
- 0 kill rule atteinte ET non-max-E[R]-de-cohort → Leg 2 non-pick
- 0 kill rule atteinte ET max-E[R]-de-cohort → Stage 1 gate (schéma α'' + 4w canonical)

---

**Statut** : SPECIFIED_READY (full infra exists, prêt pour exécution).
