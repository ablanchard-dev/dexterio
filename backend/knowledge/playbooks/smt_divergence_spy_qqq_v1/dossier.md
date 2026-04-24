# SMT_Divergence_SPY_QQQ_v1 — Dossier §18 (Plan v4.0 §0.5bis entrée #1)

**Statut initial** : SPECIFIED_BLOCKED_BY_INFRA_PARTIAL (§0.B briques livrées mais HTF sweep event wiring dans setup_engine_v2 à câbler) → SPECIFIED_READY après wiring.

---

## Pièce A — Fiche d'identité

| Champ | Valeur |
|---|---|
| **Nom canonique** | `SMT_Divergence_SPY_QQQ_v1` |
| **Version** | v1 |
| **Famille** | `smt_cross_index` (nouvelle famille — premier playbook dual-asset DexterioBOT, 0/30 playbooks historiques utilisaient un dual-asset gate per 04_CODE_AUDIT §3) |
| **Type** | `cross_timeframe` + `multi-leg` (SPY+QQQ simultané, entrée sur lagging index) |
| **Instruments** | `SPY, QQQ` (pair corrélée, dual-asset gate obligatoire) |
| **Timeframes** | HTF pool (4H > 1H) + setup TF (5m k3 pivots) + execution 1m |
| **Direction** | `both` (bull divergence → LONG lagging ; bear divergence → SHORT lagging) |
| **Régime visé** | Toutes sessions RTH, focus NY open via §0.B.5 macro kill zone 09:50-10:10 (option PM 13:50-14:10) |
| **Statut initial** | `SPECIFIED_BLOCKED_BY_INFRA_PARTIAL` |
| **Auteur / origine** | TRUE `FJch02ucIO8` (TJR "One Simple Confluence") + TRUE `7dTQA0t8SH0` (TJR SMT Divergence) + MASTER ligne 12745-12841 (convergence 100%). Plan v4.0 §0.5bis entrée #1. |
| **Dernière review** | 2026-04-24 |

---

## Pièce B — Hypothèse formelle (5 sous-blocs)

### Thèse
Quand un pool de liquidité HTF (4H ou 1H) fresh est sweeped sur SPY+QQQ simultanément et que **les deux indices divergent** dans leur structure post-sweep (l'un casse la structure counter-trend = leading, l'autre continue = lagging), le lagging rattrape le leading dans la direction du leading. Le TP canonique est le "SMT completion" = attached swing H/L du pool sweeped (price retrace vers ce niveau).

### Mécanisme (pourquoi ça devrait être tradable)
SPY et QQQ sont corrélés structurellement (~0.85 daily). Un sweep HTF synchrone génère un short-term imbalance de liquidité. Si **seul un des deux fait un break structurel** (LH en uptrend, HL en downtrend) pendant que l'autre continue la tendance, ça signale que **l'exhaustion a commencé mais n'est pas complète** — le lagging n'a pas encore capitulé. Le trade capture le mouvement de rattrapage (convergence des deux indices dans la direction du leading).

Le TP "SMT completion" cible le swing qui a créé le pool (origin point) parce que c'est là que la liquidité résiduelle attire le price après la divergence.

### Conditions de fertilité
- Sessions NY RTH (09:30-16:00 ET), surtout macro kill zone 09:50-10:10 (§0.B.5)
- Corrélation SPY/QQQ haute (>0.8 rolling daily)
- Volatilité fertile §0.4-bis (VIX 15-25)
- Structure HTF visible (HH-HL ou LL-LH claire sur 4H ou 1H)
- Pools 4H/1H fresh (§0.B.7) : non-sweeped depuis session précédente au minimum

### Conditions de stérilité
- Corrélation SPY/QQQ cassée (regime shift, un seul indice répond à un catalyseur sectoriel — earnings QQQ large-cap tech déconnecté de SPY)
- Vol panic >25 ou vol low <15 : mean-rev intraday non-fiable
- Weekend / holiday sessions (thin liquidity)
- Outside macro kill zones si `strict_manip_gate=true`
- HTF bias neutre/mixed (§0.B.3 insufficient pattern) : signal structurel absent
- Pas de FVG HTF respecté à proximité du sweep (pas de reference structurelle valide)

### Risque principal (= falsifiabilité)
Hypothèse **réfutée** si : sur un corpus de n ≥ 15 setups canon-faithful (sweep HTF fresh + divergence SMT + toutes les §0.B briques actives), `E[R]_pre_reconcile ≤ 0.05R` OR `peak_R p60 ≤ 0.5R` OR `WR < 30%`. La divergence SMT ne porte pas d'edge au-delà du bruit corrélation SPY/QQQ.

Hypothèse **sous-exercée** (Cas B §20) si : n < 5 sur smoke nov_w4 ou n < 15 sur 4w Stage 1 — la fenêtre de convergence "sweep HTF + divergence structurelle simultanée" est trop rare. Dans ce cas, élargir corpus (Cas A1 §20) avant de conclure.

---

## Pièce C — Spécification d'état décisionnel

**Type** : stateful séquentiel (pas stateless instant — nécessite observation d'un sweep HTF puis attente de la structure divergente).

### États (per-symbol-pair state, managed via Aplus01Tracker pattern réutilisé)

```
IDLE
  ↓ (pool HTF 4H/1H fresh sweeped sur SPY OR QQQ, §0.B.7 mark_swept emit)
POOL_SWEEPED (timeout: 30 bars 5m = 150 min)
  ↓ (k3 post-sweep pivots classifiable sur les 2 indices, min 1 high + 1 low par côté post sweep_ts)
STRUCTURE_OBSERVABLE (timeout: 20 bars 5m = 100 min)
  ↓ (§0.B.2 detect_smt_divergence → SMTSignal émis avec leading + direction + smt_completion_target)
SMT_SIGNAL_EMITTED (timeout: 6 bars 5m = 30 min ; entrée doit arriver rapidement ou setup périmé)
  ↓ (§0.B.3 htf_bias_structure bias ≠ neutral AND aligné avec SMT direction, §0.B.5 macro kill zone pass, §0.B.6 daily_profile allowed, §0.B.8 pre-sweep gate OK)
EMIT_SETUP (setup livré à setup_engine_v2 avec entry_price = lagging.last_close)
```

### Point d'armement
Un pool HTF (4H ou 1H) fresh est sweeped sur SPY OU QQQ. Le sweep est détecté via `PoolFreshnessTracker.update(bar_ts, high, low)` qui retourne pool_ids swept. L'état `POOL_SWEEPED` commence avec `sweep_ts` = bar timestamp.

### Point de confirmation
Deux sous-étapes :
1. **STRUCTURE_OBSERVABLE** : attendre que chaque indice ait au moins 2 pivots k3 post-sweep_ts (1 high + 1 low) pour que `classify_last_pivot` puisse retourner HH/LH/HL/LL.
2. **SMT_SIGNAL_EMITTED** : `detect_smt_divergence(a=SPY_inputs, b=QQQ_inputs, sweep_ts=sweep_ts)` retourne un `SMTSignal` non-null. Bear ou bull divergence, indifféremment.

### Point d'émission setup
État EMIT_SETUP reached AND :
- `htf_bias.bias` (SPY ou QQQ leading) non-neutral ET aligné avec `signal.direction`
- `check_macro_kill_zone(current_ts, macro_am=True, macro_pm=True)` passe
- `daily_profile.classify_session_profile(bars_today).profile` in `[manipulation_reversal, manipulation_reversal_continuation, undetermined]` (consolidation → reject)
- `check_pre_sweep_gate(sweep_event_ts=sweep_ts, current_ts, max_window_minutes=30)` passe

Le setup est émis avec :
- `symbol = signal.lagging_symbol`
- `direction = signal.direction`
- `entry_price = signal.lagging_entry_reference` (lagging last_close)
- `tp_logic = smt_completion`, `tp_logic_params = {smt_completion_price: signal.smt_completion_target, fallback_rr: 2.0, reject_on_fallback: true}`
- `sl_logic = swing_structure` (k3 opposite-direction swing, pad 3 ticks)

### Point d'invalidation
- **Timeout** dans chaque état (voir ci-dessus) → reset vers IDLE
- **Counter-structure** : si pendant SMT_SIGNAL_EMITTED le leading fait la structure opposée (ex signal bear → leading fait HH après son LH) → reset IDLE
- **Trading day rollover** 18:00 ET → reset + wipe session-scoped pools via PoolFreshnessTracker
- **Bias HTF flip** (§0.B.3 `flipped_at` set) → reset IDLE si le flip contredit la signal direction

---

## Pièce D — Dépendances moteur + audit infra

### Détecteurs requis
| Détecteur | Status | Source |
|---|---|---|
| SMT cross-index HTF-anchored | ✅ §0.B.2 DONE | [smt_htf.py](backend/engines/patterns/smt_htf.py) |
| FVG / IFVG detectors (pour pool origin / HTF bias) | ✅ legacy OK | [ifvg.py](backend/engines/patterns/ifvg.py), [ict.py](backend/engines/patterns/ict.py) |
| Stacked FVG rule + pre-sweep gate | ✅ §0.B.8 DONE | [fvg_stacking.py](backend/engines/patterns/fvg_stacking.py) |

### Trackers requis
| Tracker | Status | Source |
|---|---|---|
| PoolFreshnessTracker per-symbol | ✅ §0.B.7 DONE | [pool_freshness_tracker.py](backend/engines/features/pool_freshness_tracker.py) |
| State machine SMT cross-index (5 états IDLE→EMIT) | 🚧 À construire post-dossier — réutilise Aplus01Tracker pattern | À créer : `backend/engines/features/smt_cross_index_tracker.py` |

### Helpers géométriques / features
| Helper | Status | Source |
|---|---|---|
| directional_change k3/k9 pivots | ✅ legacy, DST-safe, LRU cached | [directional_change.py](backend/engines/features/directional_change.py) |
| htf_bias_structure 7-step | ✅ §0.B.3 DONE | [htf_bias_structure.py](backend/engines/features/htf_bias_structure.py) |
| equilibrium_zone most-recent | ✅ §0.B.4 DONE (non-critique pour SMT v1, réserve pour v2) | [equilibrium_zone.py](backend/engines/features/equilibrium_zone.py) |

### Logique de session
| Item | Status | Source |
|---|---|---|
| session_range_tracker (Asia/London/NY) | ✅ legacy | [session_range.py](backend/engines/session_range.py) |
| Macro kill zone gate (§0.B.5) | ✅ DONE | [entry_gates.py](backend/engines/execution/entry_gates.py) |
| Daily profile filter (§0.B.6) | ✅ DONE | [daily_profile.py](backend/engines/features/daily_profile.py) |
| Trading day rollover 18:00 ET | ✅ legacy, DST-aware | SessionRangeTracker + compute_trading_date |

### SL logic requise
- `sl_logic: swing_structure`, `pivot_level: k3`, `padding_ticks: 3`
- SL placé au swing opposite du lagging index au moment du setup (k3 last swing low pour LONG, last swing high pour SHORT)
- Sanity : `sl_distance > 0` (enforcé par tp_resolver)

### TP logic requise
- `tp_logic: smt_completion` (§0.B.1 DONE)
- `tp_logic_params`:
  - `smt_completion_price`: fourni par SMTSignal.smt_completion_target
  - `fallback_rr: 2.0`
  - `reject_on_fallback: true` (Option ε pattern) — si smt_completion_price invalide OR wrong-side → trade rejeté entièrement, pas de fallback silencieux à 2R

### Risk hooks particuliers
- **Dual-asset exposition** : le setup ouvre une position sur le **lagging** uniquement. SPY ou QQQ, pas les deux. Pas de hedged pair trade en v1 (simplicité).
- **Cap intra-session** : respecte `max_setups_per_session` playbook YAML (default 2 comme Aplus_01 v1).
- **Cooldown** : post-trade cooldown 15 min (évite setups consécutifs sur le même sweep event résiduel).

### Champs runtime journal requis
En plus des champs standards (`tp_reason`, `structure_alignment_counter`) :
- `smt_leading_symbol` : SPY ou QQQ
- `smt_lagging_symbol` : inverse
- `smt_divergence_type` : "bull" | "bear"
- `smt_pool_sweep_tf` : "4h" | "1h"
- `smt_pool_sweep_ts` : timestamp UTC
- `smt_completion_target_price` : TP target
- `htf_bias_enforced_method` : "structure_k9_7step" (vs legacy "SMA_5")
- `htf_bias_confidence` : float 0-1 (§0.B.3 output)
- `daily_profile_classified` : "manipulation_reversal" | "manipulation_reversal_continuation" | "undetermined"
- `pre_sweep_window_minutes` : 30 (config value)
- `latency_ms_simulated` : existant (§0.7 G2)
- `slippage_R_vs_ideal` : existant (§0.7 G1+G3 reconcile)

### Résultat audit infra
`partial infra exists` → statut `SPECIFIED_BLOCKED_BY_INFRA_PARTIAL`.
**Briques manquantes** :
1. `smt_cross_index_tracker.py` — state machine per-symbol-pair (5 états), pattern Aplus01Tracker réutilisable, ~100 LOC + tests unitaires.
2. Wiring dans `setup_engine_v2.py` : hook post-`required_signals` gate, avant tp_resolver. Tracker consomme `pool_sweep_events` (nouveau event bus ou polling depuis PoolFreshnessTracker per symbol).
3. Bootstrap des HTF pools dans la boucle backtest : à chaque bar HTF (4H / 1H) close, extraire swing H et swing L k9 et les enregistrer dans PoolFreshnessTracker comme pool candidats.

**Plan chantier** : post-dossier review utilisateur, ~1j tracker + wiring + 10 tests intégration + smoke nov_w4.

---

## Pièce H — Kill rules pré-écrites + verdict template

### Kill rules pré-écrites (smoke nov_w4)

| # | Condition | Action |
|---|---|---|
| R1 | n < 5 sur smoke nov_w4 | **Cas A1** §20 PEDAGOGICAL_INFRA_TEST → élargir corpus 4w Stage 1 avant kill. PAS d'ARCHIVE prématuré. |
| R2 | n ≥ 5 ET `E[R]_gross ≤ 0` | ARCHIVED Cas C §20 + entrée #2 auto (Aplus_01_v2 TRUE HTF enriched) |
| R3 | n ≥ 15 ET `E[R]_gross > 0` mais `peak_R p80 < 0.5R` | ARCHIVED Cas C signal faible (divergence corrélation bruit) |
| R4 | Tests niveau 1 (unitaires tracker) ou niveau 2 (intégration) FAIL | Retour phase D (recoder), pas SMOKE_PENDING |
| R5 | `htf_bias_enforced_method` ≠ `structure_k9_7step` dans > 5% des trades | Wiring cassé → re-audit setup_engine_v2 hook |
| R6 | `tp_reason` distribution < 50% `smt_completion` OR > 50% `reject_on_fallback_no_smt_completion` | SMT target extraction broken — re-audit smt_htf.py attached_swing_price pipeline |

### Budget §19.3
Max 3 itérations post-smoke. Itération = ajustement d'UN paramètre justifié par l'hypothèse (ex : `max_window_minutes` pre-sweep gate 30→45, timeout SMT_SIGNAL_EMITTED 6→8 bars). PAS tuning de seuils arbitraires.

### Gate Stage 1 (après smoke PASS)
Si smoke nov_w4 passe les kill rules → 4 semaines canoniques (jun_w3 + aug_w3 + oct_w2 + nov_w4) en backtest-realistic (ConservativeFillModel G1+G3 + LatencyModel G2). Bar Stage 1 :
- `E[R]_pre_reconcile > 0.05R`
- `n ≥ 15`
- `peak_R p60 > 0.5R`
- Split régime ≥3/5 régimes §0.4-bis (sessions / vol_band / trend / news / dow)
- 0 weeks < -0.5R

Gate Stage 2 (après Stage 1 PASS) : `E[R]_net > 0.10R` (post -0.097R/trade reconcile) + `n ≥ 15` + `PF > 1.2` + G5 Stress+MC PASS (si G5 livré).

Gate Stage 3 (après Stage 2 PASS) : 3 mois cross-regime ≥5 régimes + O5.3 (bar permutation p<0.05 + Sharpe>1 + Martin>1) + `E[R]_net > 0.10R` + `n ≥ 30` → **§0.3 point 2 déclenché** (1er product-grade validé cross-regime, review humaine obligatoire avant paper Stage 4).

### Verdict template (§18.3 5-blocs)

À générer via [build_verdict.py](backend/scripts/build_verdict.py) avec YAML config contenant :

**Bloc 2 métriques (v4 REVISE champs)** : n, WR, PF, E[R]_gross/pre_reconcile/net, deltas, peak_R p50/p80, mae_R p20, DD, avg duration, delta ideal vs realistic, **htf_bias_enforced** = structure_k9_7step (pas SMA_proxy), **pool_freshness_active** = True, **smt_gate_applied** = True, **décote_académique** = False (non publié, pas académique), **g5_stress_mc_passed** = TBD post-G5.

**Bloc 3 lecture structurelle** : catégorie audit initiale (SPECIFIED → IMPLEMENTED → SMOKE_PENDING → SMOKE_PASS/FAIL) ; distribution leading/lagging (SPY vs QQQ) ; % `smt_completion` vs `reject_on_fallback_no_smt_completion` ; split régime détail.

**Bloc 4 décision** : continuer / itérer / tuer / promouvoir per kill rules.

**Bloc 5 why** : référence kill rules R1-R6 ; précision sur hypothèse A (MASTER mal codé) vs B (MASTER arbitré) — §0.3 point 3bis applicable après 3 entrées §0.5bis #1+#2+#3 testées.

---

## Pointeurs

- **YAML** : [smt_spy_qqq_v1.yml](../../campaigns/smt_spy_qqq_v1.yml) (à créer)
- **Tests** : [tests/](./tests/) (à créer)
- **Protocol run** : [protocol.md](./protocol.md) (à créer)
- **Verdicts** : [verdicts/](./verdicts/) (post-smoke)
- **Briques canon §0.B** : voir [backend/knowledge/brain/01-04_*.md](../../brain/) + code dans backend/engines/features/ + patterns/ + execution/
- **Plan source** : `/home/dexter/.claude/plans/parsed-nibbling-kettle.md` §0.5bis entrée #1
