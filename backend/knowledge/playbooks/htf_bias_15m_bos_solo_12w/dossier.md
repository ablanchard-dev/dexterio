# Dossier — HTF_Bias_15m_BOS solo 12w (Leg 2.3 Quarantine PROMOTE)

**Source** : CEO arbre §0.5 Leg 2 — candidats CLAUDE.md "quarantine" E[R]>0 sur n=3-11 : **besoin data, pas calibration**.

---

## Pièce A — fiche d'identité

| Champ | Valeur |
|---|---|
| Nom canonique | HTF_Bias_15m_BOS (baseline playbooks.yml L821) |
| Version solo-run | 12w corpus expansion v1 |
| Famille | MASTER Aplus_04 — HTF bias + 15m BOS after sweep, 1m entry on pullback to FVG/OB |
| Type | Stateless 15m + 1m confirmation (require_sweep + require_bos) |
| Instruments | SPY, QQQ |
| Timeframes | 15m setup + 1m confirmation |
| Direction | with_bias (aligné HTF bullish/bearish) |
| Régime visé | trend + manipulation_reversal, structure uptrend/downtrend |
| Statut initial | quarantine (CLAUDE.md — E[R]>0 sur n=3-11 à valider sur corpus élargi) |
| Auteur | baseline playbook v0 (MASTER Family B transcripts) |
| Dernière review | 2026-04-22 (Leg 2.3 démarrage) |

---

## Pièce B — hypothèse formelle

### Thèse
Sur setup 15m BOS (break of structure) avec require_sweep + require_bos, la 1m confirmation à fvg_retest capture la continuation aligned HTF bias. Le timeframe 15m filtre le bruit 5m tout en restant intraday actionable.

### Mécanisme
BOS = confirmation structure cassée (lower-high/higher-low dépassé). Sweep préalable drain stops opposés. FVG retest = pullback institutionnel avant continuation. 1m confirm évite faux-BOS. Aligné HTF = évite contre-tendance.

### Conditions de fertilité
- Session NY 09:30-12:00 (fenêtre ouverture large)
- htf_bias bullish OU bearish (pas range)
- structure_htf uptrend OU downtrend
- day_type trend OU manipulation_reversal
- ADX ≥ 20
- require_sweep=true (liquidité drain préalable)
- require_bos=true (structure cassée)
- pattern_confirmations ≥ 2

### Conditions de stérilité
- Range pur (ADX < 20)
- Absence sweep ou BOS
- htf_bias neutral / unknown

### Risque principal (falsifiabilité)
Si **E[R]_gross ≤ 0 sur n ≥ 20 trades 12 weeks**, l'hypothèse HTF 15m BOS isolée est réfutée (corroborerait Aplus_04 Option B E[R]=-0.074 sur 4w). Alternative possible : combine avec schema α'' (liquidity_draw) mais cela sort du scope "besoin data pas calibration".

---

## Pièce C — spécification d'état décisionnel

**Stateless** avec conditions multiples :

1. **Détection setup (15m)** : BOS détecté + sweep préalable + pattern_confirmations ≥ 2.
2. **Gate context** : htf_bias bullish/bearish aligné + structure uptrend/downtrend + ADX ≥ 20 + day_type allowed.
3. **Entry 1m** : LIMIT à zone `fvg_retest`, confirmation_tf=1m.
4. **SL swing** : recent_swing ± 3 ticks (padding plus large que IFVG).
5. **TP fixed RR** : 3.0/5.0 (baseline inchangé).
6. **Invalidation** : SL touché OR EOD.

---

## Pièce D — dépendances moteur + audit infra

| Brique | Status | Fichier |
|---|---|---|
| BOS detector (15m) | ✓ (engine sanity v2 B4) | [backend/engines/patterns/bos.py](backend/engines/patterns/bos.py) |
| Sweep detector | ✓ (engine sanity v2 B3) | [backend/engines/patterns/sweep.py](backend/engines/patterns/sweep.py) |
| FVG retest zone | ✓ (engine sanity v2 B1) | [backend/engines/patterns/fvg.py](backend/engines/patterns/fvg.py) |
| 1m confirmation gate | ✓ | [backend/engines/execution/entry_gates.py](backend/engines/execution/entry_gates.py) |
| Swing SL logic | ✓ | [backend/engines/execution/stop_loss.py](backend/engines/execution/stop_loss.py) |
| TimeframeAggregator 15m | ✓ (engine sanity v2 C7) | [backend/engines/timeframe_aggregator.py](backend/engines/timeframe_aggregator.py) |
| ADX gate | ✓ | [backend/engines/features/adx.py](backend/engines/features/adx.py) |

**Résultat audit** : `full infra exists` — aucun chantier requis.

---

## Pièce E — YAML d'exécution

Baseline **as-is** (playbooks.yml L821). Pas d'override. Solo-run via `--calib-allowlist HTF_Bias_15m_BOS`.

---

## Pièce F — tests

Aucun test dédié (baseline déjà couvert par engine_sanity_v2 B1/B3/B4 + C7).

---

## Pièce G — protocole de run

Corpus identique à Leg 2.1 — 12 semaines jun-nov 2025.

### Mode de run
- AGGRESSIVE + ALLOW_ALL_PLAYBOOKS + `--calib-allowlist HTF_Bias_15m_BOS`
- `--no-relax-caps` (caps actives)
- Fill model : Ideal

### Commande canonique par semaine
```bash
cd backend && .venv/bin/python scripts/run_mini_lab_week.py \
  --start <YYYY-MM-DD> --end <YYYY-MM-DD> \
  --label htf_bias_15m_bos_solo_12w_<week_label> \
  --output-parent htf_bias_15m_bos_solo_12w \
  --no-respect-allowlists --no-relax-caps \
  --calib-allowlist HTF_Bias_15m_BOS
```

---

## Pièce H — kill rules pré-écrites

### Gate Leg 2 cohort (plan §0.5)
> Kill rule cohort : si 0/3 passe E[R] > 0.05R gross + n ≥ 20 → Leg 3

### Kill rules individuelles HTF_Bias_15m_BOS 12w
1. **n < 20 trades sur 12 semaines** → ARCHIVED (signal rare — précédent Aplus_04 Option B 4w avait n=55 / 4w, donc 12w devrait donner n~150 si détecteur calme ; si n<20 = détecteur cassé)
2. **E[R]_gross ≤ 0** → ARCHIVED (Cas §20 C ; Aplus_04 Option B 4w −0.074 net point de comparaison)
3. **E[R]_gross ∈ [0, +0.05R] ET n ≥ 20** → MARGINAL, pas promotion
4. **E[R]_gross > 0.05R ET n ≥ 20** → PASS Leg 2 criterion

**Note comparaison Aplus_04_v1 Option B** : 4w E[R]=-0.074 / net -0.139, n=55. Si HTF_Bias_15m_BOS 12w ~replicate ce pattern (n~150, E[R]<-0.05), hypothèse Family B HTF+15m BOS isolée structurellement réfutée. Si E[R] s'améliore significativement (direction corpus-expansion), warrant investigation.

---

**Statut** : SPECIFIED_READY.
