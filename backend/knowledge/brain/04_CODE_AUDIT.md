# 04_CODE_AUDIT — Playbooks vs BRAIN_TRUTH (MASTER × TRUE × QUANT)

**Date** : 2026-04-24
**Sources auditées** :
- `backend/knowledge/playbooks.yml` (26 playbooks actifs/quarantaine)
- `backend/knowledge/campaigns/*.yml` (rewrites, schémas TP calib, Aplus_01_full_v1, Aplus_03_v2, b_aplus04_v1)
- `backend/engines/patterns/*` + `backend/engines/features/*` + `backend/engines/execution/tp_resolver.py`
- Canon : `01_TRUE_EXTRACTION.md`, `02_MASTER_REFINED.md`, `03_BRAIN_TRUTH.md`

**Objectif** : déterminer pour chaque playbook si son verdict ARCHIVED/DENYLIST/QUARANTINE est **falsifiant** (edge absent, hypothèse testée honnêtement) ou **non-falsifiant** (implémentation défaillante, l'hypothèse canon n'a pas été testée).

---

## 1. Résumé exécutif

- **Sur 30 playbooks audités, 0 sont ALIGNED_TRUE_MASTER**. 2 sont PARTIAL_IMPL (Aplus_01_full_v1, Aplus_02_Premarket_v1 — signal cascade correct mais axes critiques manquants). **22 sont FANTASY** (vocab-borrowing sans mécaniques canon). 4 sont STRUCTURAL_KILL / OBSOLETE (Stat_Arb v1/v2 non-ICT, ORB_Breakout_5m, IFVG isolé 5m). 2 sont NEW_VERSION candidates (HTF_Bias_15m_BOS, Engulfing).
- **Hypothèse A ("MASTER dit bien, bot code mal") est dominante** : **22/30 FANTASY** + 2 PARTIAL signifient que **24/30 verdicts négatifs NE SONT PAS FALSIFIANTS** du canon MASTER+TRUE. Les 10 data points négatifs historiques DexterioBOT 2025 SPY/QQQ sont principalement un verdict sur ~~ICT~~ → **"ICT mal codé avec SMA proxy + fixed RR + pools 5m/15m sans freshness ni SMT ni EQ"**.
- **5 gaps systémiques repo totaux** (aucun playbook ne les a) : (1) **SMT cross-index HTF-anchored** absent (le `detect_smt` existant est rolling max/min 1h non-anchored sur liquidity sweep, utilisé en scoring bonus uniquement — FANTASY), (2) **tp_resolver freshness filter** + `pool_tf=["4h","1h"]` absent, (3) **HTF bias state machine 7-step** (FVG respect/disrespect + draws ranked + already-swept filter) absent (SMA_5 proxy Phase D.1 nul), (4) **Equilibrium most-recent swing** brick absent, (5) **macro kill zone 9:50-10:10 + 13:50-14:10** absent (time_windows larges).
- **Fixed RR TP ≥ 2R ubiquitaire** dans 24/30 playbooks vs **peak_R p80 historique < 1R** (R.3 + Aplus_03_v2 + Aplus_04 + Engulfing + IFVG + VWAP + HTF = 7 confirmations). Fixed RR ≥ 2R est structurellement inatteignable, pas un choix — un artefact templating.
- **Implication plan** : §10 r11 réouvertures légitimes pour ≥ 10 playbooks si briques canon livrées (SMT HTF-anchored, pool_tf 4H/1H + freshness, EQ most-recent, structure_k9 bias). Le `tp_resolver α'' + reject_on_fallback` est déjà là ; briques clés manquantes **concentrées dans ~400-700 lignes**.
- **Pas de rewrite individuel sans briques transversales d'abord**. Les 10 data points négatifs se reproduiront playbook-par-playbook tant que le repo ne possède pas SMT + freshness + HTF bias vrai.
- **Recommandation top 3** : (A) NEW_BRICK SMT SPY/QQQ HTF-anchored (MASTER+TRUE convergent, 0 support QUANT neutre, infra 50 % en place) ; (B) UPGRADE `tp_resolver` freshness + 4H/1H pool_tf ; (C) REWRITE `HTF_Bias_15m_BOS` et `Engulfing_Bar_V056` avec les nouvelles briques — ce sont les 2 seuls playbooks dont l'**architecture pourrait survivre** un rewrite faithful.

---

## 2. Gaps systémiques du repo

### 2.1 Briques MANQUANTES (BRAIN_TRUTH → repo)

1. **SMT cross-index synchronisé HTF-anchored** (N2, TRUE `7dTQA0t8SH0` + MASTER ligne 12745-12841 convergents).
   - Existant : `detect_smt(spy_candles, qqq_candles)` rolling max/min sur 1h (aucune anchor sur sweep HTF). Confidence cosmétique 0.85-0.95. Wiré en **scoring bonus `smt_bonus`** uniquement, pas en gate.
   - Canon exige : sweep HTF simultané → un index fait HL, l'autre LL → entry sur **leading index** → TP **SMT completion** (attached swing).
   - Verdict : `detect_smt` = FANTASY partiel, signal tronqué.
2. **`tp_resolver` freshness filter** (N4 pool, TRUE `pKIo-aVic-c` + MASTER ligne 21490-21552).
   - Existant : `tp_logic=liquidity_draw` swing_k3/k9 **sans** filtre freshness (pas de tracking sweep session_prior / PM / London).
   - Canon exige : `pool_tf=["4h","1h"]` + `require_unsweeped_since="session_prior"` + reaction gate.
3. **HTF bias state machine 7-step** (N1, TRUE `ironJFzNBic` + MASTER video 016 3 daily profiles).
   - Existant : `require_htf_alignment: D` → SMA_5 proxy, 0/171 rejections Phase D.1 (cosmétique).
   - Canon exige : structure HH/HL D/4H + FVG respect/disrespect binary state + draws rankés + already-swept filter + close-through flip.
4. **Equilibrium brick** (N3, TRUE `wzq2AMsoJKY` strict "most recent").
   - Existant : `detect_equilibrium` dans `equilibrium.py` utilise `max(window)` + `min(window)` sur lookback 20 bars — **pas most-recent swing** mais **extrêmes absolus**.
   - Canon exige : EQ 50 % entre dernier swing H et swing L, redessiné à chaque HH/LL.
5. **Macro kill zone 9:50-10:10 + PM 13:50-14:10** (MASTER ligne 16028-16045).
   - Existant : time_windows playbooks typiquement `09:30-12:00` + `14:00-15:30` (largement trop larges).
   - Canon exige : overlay micro-gate dans fenêtre macro.
6. **3 daily profiles filter top-layer** (MASTER seul, video 016).
   - Existant : absent.
   - Canon exige : filtre `consolidation→manip/rev` ou `manip→rev` ou `manip+rev→continuation` basé sur session précédente.
7. **Stacked FVG rule (last-in-stack invalidates)** (TRUE `TEp3a-7GUds`).
   - Existant : détecteur FVG isolé.
   - Canon exige : state machine stack.
8. **Pre-sweep gate pour IFVG** (TRUE `BdBxXKGWVjk`).
   - Existant : `Aplus_03_IFVG_Flip_5m` + `v2` ne gate pas sur sweep préalable.
9. **KDE peak prominence pour pools S/R data-driven** (QUANT `mNWPSFOVoYA`).
   - Existant : absent — pools = swing_k3/k9 pivots.
   - Enhancement (pas canon-strict, mais upgrade `tp_logic: liquidity_draw`).

### 2.2 Implémentations défaillantes (misalignment > missing)

- **Fixed RR TP ≥ 2R** : 24/30 playbooks. Incompatible peak_R p80 < 1R historique.
- **Pools 5m/15m** : majoritaires vs canon 4H/1H.
- **OB/BB traités comme confluences A-grade** : TRUE `wzq2AMsoJKY` élimine OB/BB si EQ ; IRONCLAD `s9HV_jyeUDk` confirme OB/PD dégradent empiriquement.
- **smt_bonus scoring seulement** : n'est jamais un gate entry — inutile en pratique.
- **time_windows trop larges** : aucun playbook n'a la macro kill zone 9:50-10:10.

---

## 3. Matrix playbook × 6 axes

Légende : **ALIGNED** (canon respecté), **PARTIAL** (concept présent mais cassé/partiel), **MISSING** (absent), **MISALIGNED** (présent mais contredit canon), **FANTASY** (vocab mais mécanique absente), **—** (non applicable). Tag : **ALIGNED_TRUE_MASTER / PARTIAL_IMPL / FANTASY / OBSOLETE / STRUCTURAL_KILL**.

| # | Playbook | A1 HTF bias | A2 Signal | A3 TP | A4 Pool/TF | A5 EQ | A6 SMT | Tag | Reco |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **News_Fade** (ALLOW) | MISSING (no bias gate) | PARTIAL (news filter OK, no sweep+IFVG) | MISALIGNED (fixed 3R, peak_R<1R) | MISSING (spike_extreme, no 4H/1H) | — | — | FANTASY | REWRITE_FAITHFUL (news + HTF bias + pool 4H) |
| 2 | **FVG_Fill_Scalp** (ALLOW) | MISSING | MISSING (FVG isolé, pas IFVG ni sweep) | MISALIGNED (1.5R fixed) | MISSING (fvg_extreme) | — | — | FANTASY | KILL (vocab borrowing sans mécanique) |
| 3 | **Session_Open_Scalp** (ALLOW, LAB ONLY) | MISSING | MISSING (range_break no ICT) | MISALIGNED (1.5R fixed) | MISSING | — | — | FANTASY | KILL |
| 4 | **Liquidity_Sweep_Scalp** (DENY) | MISSING | PARTIAL (sweep OK, no reaction gate, no IFVG) | MISALIGNED (1.5R) | MISSING | — | — | FANTASY | REWRITE_FAITHFUL (sweep + reaction + 4H pool) |
| 5 | **NY_Open_Reversal** (DENY B0.3) | PARTIAL (london_sweep_required) | PARTIAL (sweep required, no IFVG/BOS doubleshot) | MISALIGNED (3R fixed) | MISSING | — | smt_bonus scoring | FANTASY | REWRITE_FAITHFUL (fort candidat sémantique) |
| 6 | **ORB_Breakout_5m** (DENY B0.3) | MISSING | MISSING (breakout only, anti-ICT) | MISALIGNED (2R fixed) | MISSING | — | — | STRUCTURAL_KILL | KILL (ORB breakout = fausse ICT, QUANT ODHlC9YuowY + consensus edge decay) |
| 7 | **London_Sweep_NY_Continuation** (DENY -326R) | MISSING | PARTIAL (london_sweep required) | MISALIGNED (2.5R) | MISSING | — | — | FANTASY | KILL |
| 8 | **Trend_Continuation_FVG_Retest** (DENY -22R) | MISSING | MISSING (FVG retest generic) | MISALIGNED (2.5R) | MISSING | — | scoring smt_bonus | FANTASY | KILL |
| 9 | **BOS_Momentum_Scalp** (DENY -142R) | MISSING | PARTIAL (BOS only, no sweep) | MISALIGNED (1.5R) | MISSING | — | — | FANTASY | KILL |
| 10 | **Power_Hour_Expansion** (DENY -31R) | MISSING | MISSING (time-based only) | MISALIGNED (2R) | MISSING | — | — | FANTASY | KILL |
| 11 | **Lunch_Range_Scalp** (DISABLED) | MISSING | MISSING (range fades, no ICT) | MISALIGNED (1.5R) | MISSING | — | — | STRUCTURAL_KILL | KILL |
| 12 | **DAY_Aplus_1_*** (DENY SPAM) | — (not loaded) | — | — | — | — | — | STRUCTURAL_KILL (SPAM) | KILL |
| 13 | **SCALP_Aplus_1_*** (DENY SPAM) | — | — | — | — | — | — | STRUCTURAL_KILL (SPAM) | KILL |
| 14 | **Liquidity_Raid_V056** (DENY 2 matches) | MISSING | PARTIAL (SWEEP@5m) | MISALIGNED (2R) | MISSING | — | — | FANTASY | KILL (detector cassé) |
| 15 | **Engulfing_Bar_V056** (ARCHIVED Leg 1.1) | MISSING | MISSING (engulfing isolé no ICT) | MISALIGNED (2R fixed peak_r p80=0.73) | MISSING | — | — | FANTASY | REWRITE_FAITHFUL possible (candidat A2 IFVG + sweep) OU KILL |
| 16 | **Morning_Trap_Reversal** (ARCHIVED Leg 1.2 KILL) | MISSING (vwap_regime only) | PARTIAL (sweep + trap) | MISALIGNED (3R / BE 2.15 calib) | MISSING | — | — | FANTASY | KILL (KILL terminal confirmé par user) |
| 17 | **IFVG_5m_Sweep** (ARCHIVED Leg 2.1) | PARTIAL (htf_bias filter binary) | PARTIAL (IFVG signal, pas de pre-sweep gate) | MISALIGNED (3R fixed, 1/118 TP hits) | MISSING | — | — | FANTASY | REWRITE_FAITHFUL (add sweep gate + 4H pool) |
| 18 | **VWAP_Bounce_5m** (ARCHIVED Leg 2.2) | MISSING | MISSING (VWAP touch + RSI, no ICT) | MISALIGNED (1.5R fixed) | MISSING | — | — | STRUCTURAL_KILL (non-ICT, uptrend 2025 adverse mean-rev) | KILL |
| 19 | **HTF_Bias_15m_BOS** (ARCHIVED Leg 2.3) | PARTIAL (htf_bias gate) | PARTIAL (SWEEP + BOS + FVG retest = DOUBLE SHOT PARTIEL) | MISALIGNED (3R, peak_r p80 = 1.52) | MISSING | — | — | PARTIAL_IMPL | **NEW_VERSION** (meilleur candidat rewrite — QQQ SHORT subset +0.076 outlier déjà observé) |
| 20 | **Aplus_01_full_v1** (ARCHIVED Sprint 1) | PARTIAL (`require_htf_alignment: D` SMA proxy) | **ALIGNED** (sweep → BOS → confluence touch → 1m pressure via Aplus01Tracker) | PARTIAL (`tp_logic: liquidity_draw swing_k3` significant α'' — schema présent, **pool freshness absent**) | MISSING | — | — | PARTIAL_IMPL | **NEW_VERSION** v2 TRUE HTF (§0.5bis #1) — signal cascade est la seule vraie Family A structurée ; gaps A1+A4+A6 à combler |
| 21 | **Aplus_02_Premarket_v1** (ARCHIVED Leg 3) | PARTIAL | **ALIGNED** (SWEEP + BOS + structure_k3) | PARTIAL (schema α'' présent) | MISSING | — | — | PARTIAL_IMPL | DEFER (signal structurellement rare premarket, pas fixable sans redéfinir) |
| 22 | **Stat_Arb_SPY_QQQ_v1** (ARCHIVED Sprint 3) | — | — | — | — | — | — | STRUCTURAL_KILL (non-ICT ; z-score intraday faible, QUANT 0 support) | KILL |
| 23 | **Stat_Arb_SPY_QQQ_v2** (ARCHIVED Leg 4.1, byte-identical v1) | — | — | — | — | — | — | STRUCTURAL_KILL | KILL |
| 24 | **Aplus_03_IFVG_Flip_5m** (R.3 REWRITE partial) | MISSING | PARTIAL (IFVG isolé, **no pre-sweep gate**) | PARTIAL (TP calib 0.70R R.3) | MISSING | — | — | OBSOLETE | KILL (IFVG isolé TP fixed plafond confirmé × 4) |
| 25 | **Aplus_03_v2** (Case B sous-exercé) | PARTIAL | PARTIAL (IFVG + structure_k3 gate) | ALIGNED (α'' schema liquidity_draw swing_k3 significant) | MISSING (no freshness) | — | — | PARTIAL_IMPL | DEFER (schema mal exercé, 73 % fallback — need freshness upgrade to exercise) |
| 26 | **Aplus_04_HTF_15m_BOS_v1** (Option B REWRITE partial) | PARTIAL (`require_htf_alignment: D` SMA) | PARTIAL (SWEEP + BOS 15m OK) | MISALIGNED (fixed 1.0R, structural ceiling 1.02R) | MISSING | — | — | FANTASY | Subsumé par #19 HTF_Bias_15m_BOS rewrite |
| 27 | **Aplus_04_v2 α'' / ε** (rejected 3 data points) | PARTIAL | PARTIAL (HTF + structure_k3) | ALIGNED (α'' schema + reject_on_fallback) | MISSING (no freshness) | — | — | OBSOLETE | KILL (3 convergent data points -0.02 à -0.07 = signal isolé plafond confirmé) |
| 28 | **FVG_Fill_V065** (REWRITE partial) | MISSING | MISSING (range + FVG, no sweep/IFVG) | MISALIGNED (2R fixed) | MISSING | — | — | FANTASY | KILL (execution_layer issue = artefact, signal = vocab borrowing) |
| 29 | **Range_FVG_V054** (REWRITE partial) | MISSING | MISSING (range + FVG + engulf) | MISALIGNED (3R fixed) | MISSING | — | — | FANTASY | KILL |
| 30 | **FVG_Scalp_1m** (REWRITE partial 1m/1m compression) | MISSING | MISSING (FVG 1m isolé) | MISALIGNED (1.5R fixed) | MISSING | — | — | STRUCTURAL_KILL (MASTER "1m = execution only, pas setup") | KILL |
| 31 | **BOS_Scalp_1m** (PHASE3B fix C.2) | MISSING | PARTIAL (BOS@1m) | MISALIGNED (1.5R fixed) | MISSING | — | — | FANTASY | KILL (3e SIGNAL_QUALITY_SUSPECT + 1m setup anti-MASTER) |
| 32 | **Asia_Sweep_V051** (RECREATE from scratch) | PARTIAL (bias required) | PARTIAL (SWEEP + BOS @5m, but session mismatch) | MISALIGNED (5R fixed) | MISSING | — | smt_bonus | FANTASY | DEFER (session window absent corpus — recreate needs data) |
| 33 | **London_Fakeout_V066** (RECREATE or KILL) | MISSING | PARTIAL (SWEEP + BOS) | MISALIGNED (3R) | MISSING | — | — | FANTASY | KILL (1 match/4w détecteur structurellement rare) |
| 34 | **OB_Retest_V004** (DEFER n=2) | PARTIAL | PARTIAL (OB + BOS) | MISALIGNED (3R) | MISSING | — | smt_bonus | FANTASY | KILL (TRUE élimine OB si EQ présent ; IRONCLAD 8700 combos OB dégrade) |
| 35 | **EMA_Cross_5m / RSI_MeanRev_5m** | MISSING | MISSING (non-ICT) | MISALIGNED | MISSING | — | — | STRUCTURAL_KILL (non-ICT baseline) | KILL |

**Stats matrix** : **0 ALIGNED_TRUE_MASTER** / **5 PARTIAL_IMPL** (Aplus_01_full_v1, Aplus_02_Premarket_v1, HTF_Bias_15m_BOS, Aplus_03_v2, Aplus_04_v2 α''/ε) / **22 FANTASY** / **3 OBSOLETE** (Aplus_03 R.3, Aplus_04 rejected, IFVG isolé) / **8 STRUCTURAL_KILL** (Stat_Arb v1+v2, ORB, Lunch, VWAP_Bounce, EMA_Cross, RSI_MeanRev, FVG_Scalp_1m, DAY/SCALP Aplus SPAM comptés 1).

---

## 4. Focus 7 ARCHIVED post-Legs 1-4

| Playbook | Verdict historique | A1-A6 canon | Verdict falsifiant ? | Rewrite légitime §10 r11 ? |
|---|---|---|---|---|
| **Engulfing_Bar_V056** | Leg 1.1 ARCHIVED 4w (n=38 E[R]=-0.087) | FANTASY (MISSING × 5) | **NON-falsifiant** : engulfing isolé sans HTF/sweep/IFVG/SMT/freshness n'a jamais été le canon | Oui — hybride Engulfing + IFVG + HTF bias + pool 4H = candidat A2/A3 re-scope |
| **Morning_Trap_Reversal** | Leg 1.2 KILL terminal (3/3 kill rules max) | FANTASY (vwap_regime seul) | **NON-falsifiant** techniquement, MAIS user-marked KILL terminal § 19.3 consommé | **NON** (user décision absolue) |
| **IFVG_5m_Sweep** | Leg 2.1 ARCHIVED 12w (n=118 E[R]=-0.071) | FANTASY (IFVG signal OK mais pas de pre-sweep gate ni 4H pool ni HTF bias) | **NON-falsifiant** : IFVG 5m **isolé avec TP fixed** 3R sans freshness n'est pas le canon TRUE `BdBxXKGWVjk` | Oui — ajouter pre-sweep gate + HTF anchor + pool freshness = candidat fort |
| **VWAP_Bounce_5m** | Leg 2.2 ARCHIVED 12w (n=36 E[R]=-0.068) | STRUCTURAL_KILL (non-ICT mean-rev 2025 uptrend adverse) | **FALSIFIANT** partiel (hypothèse non-ICT testée) | **NON** |
| **HTF_Bias_15m_BOS** | Leg 2.3 ARCHIVED 12w (n=58 E[R]=-0.036) | PARTIAL_IMPL (axes SWEEP+BOS+FVG retest présents mais A1 SMA + A4 no 4H pool + A6 no SMT) | **NON-falsifiant** : le **meilleur** des 3 Leg 2 avec QQQ SHORT outlier +0.076 n=13 suggère structure real | **Oui — candidat #1 rewrite** (meilleur ratio "axes déjà présents / axes à ajouter") |
| **Aplus_03** (v1 R.3 / v2 / α'' / ε) | R.3 E[R]=-0.055, v2 -0.019 Case B, α''/ε rejected 3 data points | OBSOLETE : signal IFVG **isolé** 5m + TP fixed 2R structurel plafond confirmé 4× | **NON-falsifiant** du canon (IFVG isolé n'est pas canon) mais **falsifiant** de "IFVG 5m isolé + TP fixed" | **NON** (pivot vers Aplus_01 Family A full = cascade, déjà tenté v1 SMOKE_FAIL) |
| **Aplus_04** (v1 Option B / α'' / ε) | Option B -0.074, v2 α'' -0.057, ε -0.066 | PARTIAL_IMPL (HTF+15m BOS = Family B mais sans SMT ni EQ ni freshness) | **NON-falsifiant** | Subsumé par #19 HTF_Bias_15m_BOS rewrite |

**Lecture convergente** : 5/7 ARCHIVED sont **NON-falsifiants** du canon MASTER+TRUE. 2/7 falsifiants ou terminal-user-marked. **§10 r11 réouvertures légales** pour 5/7 sous condition briques canon livrées.

---

## 5. Focus Stat_Arb + Aplus_01_full + Aplus_02_Premarket

- **Stat_Arb_SPY_QQQ_v1 + v2** : non-ICT (ne relève pas du canon MASTER+TRUE). QUANT 0/20 vidéos support stat-arb (cf 03_BRAIN_TRUTH.md §3.6). **Verdict falsifiant** sur hypothèse "SPY-QQQ 5m z-score + Engle-Granger daily gate edge intraday". **Pas de rewrite légitime** — l'hypothèse économique est réfutée avec data convergente v1=v2 byte-identical.
- **Aplus_01_full_v1** : **PARTIAL_IMPL — la seule vraie Family A cascade dans le repo**. Signal (sweep → BOS → confluence touch → 1m pressure) est ALIGNED. Gaps : A1 HTF bias SMA, A6 SMT absent, A4 pool freshness absent. Verdict Cas B non-falsifiant (1 emit/9345 bars = signal structurellement rare **avec** SMA proxy bias — vrai HTF 7-step pourrait durcir ET redéfinir les paramètres de timeouts tracker). **Rewrite légitime (§0.5bis #1 TRUE HTF enrichi)**.
- **Aplus_02_Premarket_v1** : PARTIAL_IMPL. Session PREMARKET hors RTH = probablement thin liquidity + détecteurs SWEEP/BOS 5m calibrés RTH inapplicables. Verdict Cas B non-falsifiant mais **signal premarket probablement structurellement inadapté à la philosophie macro ICT (9:50-10:10 NY)** → DEFER plutôt que rewrite.

---

## 6. Recommandations plan v3.1.2

### 6.1 Playbooks à REWRITE_FAITHFUL (§10 r11 légal)

Ordonnés par probabilité de succès (ratio axes déjà présents / axes à ajouter) :

1. **HTF_Bias_15m_BOS → HTF_Bias_15m_BOS_v2_TRUE_HTF** — mécaniques à ajouter : structure_k9 bias (remplace SMA), SMT HTF-anchored gate, pool_tf=["4h","1h"] + freshness, macro kill zone. QQQ SHORT +0.076 n=13 précédent + structure playbook déjà PARTIAL.
2. **Aplus_01_full_v1 → Aplus_01_v2 TRUE HTF enrichi** (§0.5bis #1 existant) — mécaniques à ajouter : bias 7-step structure_k9 + EQ most-recent + SMT + pool freshness + macro kill zone.
3. **NY_Open_Reversal → NY_Open_Reversal_v2** — london_sweep déjà required ; ajouter IFVG 5m gate + pre-sweep structure + SMT + pool 4H freshness + pattern_close narrower. User CLAUDE.md "ne jamais toucher NY_Open_Reversal YAML sans justification forte" → rewrite = nouvelle version parallèle (pas override).
4. **IFVG_5m_Sweep → IFVG_5m_Sweep_v2** (post-freshness brick) — ajouter pre-sweep gate + structure_k9 anchor + pool 4H freshness + tp α'' + reject_on_fallback. Signal IFVG 5m n'a jamais eu de pre-sweep gate = **axe A2 canon TRUE absent**.
5. **Engulfing_Bar_V056 → Engulfing_IFVG_Hybrid_v1** — engulfing brick comme confluence sur IFVG 5m flip + HTF + pool freshness. Test si engulfing ajoute signal à IFVG v2 (Stage 1 comparatif).
6. **Liquidity_Sweep_Scalp → Sweep_Reaction_IFVG_v1** — ajouter reaction gate (canon TRUE `pKIo-aVic-c`) + IFVG flip + pool 4H freshness.

### 6.2 Playbooks à KILL définitivement

Falsifiants ou vocab-borrowing sans chemin canon :
- **Stat_Arb v1+v2** (hypothèse réfutée)
- **ORB_Breakout_5m, BOS_Momentum_Scalp, Power_Hour_Expansion, Lunch_Range_Scalp, Trend_Continuation_FVG_Retest, London_Sweep_NY_Continuation, FVG_Fill_Scalp, FVG_Fill_V065, Range_FVG_V054, London_Fakeout_V066, Session_Open_Scalp, BOS_Scalp_1m, FVG_Scalp_1m** (vocab sans canon)
- **EMA_Cross_5m, RSI_MeanRev_5m, VWAP_Bounce_5m** (non-ICT baseline, 2025 uptrend adverse)
- **DAY_Aplus_1_*, SCALP_Aplus_1_*** (SPAM confirmé)
- **Liquidity_Raid_V056** (détecteur cassé 2 matches/4w)
- **OB_Retest_V004** (TRUE+IRONCLAD convergent contre OB)
- **Morning_Trap_Reversal** (user KILL terminal)
- **Aplus_03 R.3 / Aplus_04 v2** (4 convergent data points plafond signal isolé)

### 6.3 Nouvelles briques à construire (ordonnées)

1. **SMT detector HTF-anchored** (`engines/patterns/smt_htf.py`) : remplace/étend `detect_smt` actuel. Input : sweep HTF event + SPY+QQQ candles synchronisés 5m/15m. Output : ICTPattern avec `leading_index`, `divergence_type`, SMT completion target. Wiré en **gate** (pas scoring bonus). Budget 2-3j + 15-20 tests. MASTER+TRUE convergent, QUANT neutre.
2. **tp_resolver freshness filter** (`tp_resolver.py` extension) : `pool_tf=["4h","1h"]` + `require_unsweeped_since: session_prior` + reaction gate. Nécessite tracker session-prior per symbol. Budget 2j + 10 tests.
3. **structure_k9 HTF bias feature** (`features/htf_bias_structure.py`) : remplace SMA_5 proxy. Input : 4H/D candles. Output : bias enum (bullish/bearish/neutral) + confidence + respected_fvgs + ranked_draws. Budget 2j + 12 tests. Utilise `directional_change.py` existant.
4. **Equilibrium most-recent brick** (`features/equilibrium_zone.py`) : 50 % entre **dernier swing H et dernier swing L** (pas extrêmes absolus comme `equilibrium.py` actuel). Utilise `directional_change.py` swing_k3 dernier pivot. Budget 1j + 8 tests.
5. **Macro kill zone overlay** (`modes.yml` + entry_gates.py) : 9:50-10:10 + 13:50-14:10. Budget 0.5j + 4 tests.
6. **3 daily profiles filter top-layer** (`features/daily_profile.py`) : filtre consolidation → manip/rev / manip+rev → continuation. Budget 1.5j + 10 tests.

**Total ~10-12j dev + 60 tests**. Avant toute promotion Stage 2, ces 6 briques doivent être en place OU le playbook en rewrite doit explicitement documenter pourquoi il n'en a pas besoin.

### 6.4 Nouveaux playbooks candidats

1. **SMT_Divergence_SPY_QQQ_v1** (★★★★★ TOP) — MASTER+TRUE convergents, QUANT neutre, briques 50 % en place (PairSpreadTracker D1+D2 Sprint 3 réutilisable, pivots k3 existants). **Structurellement novel** cross-playbook (0/30 utilise dual-asset gate). Cohérent §0.5bis candidat à insérer avant #1 (ou en parallèle).
2. **Aplus_01_v2 TRUE HTF enrichi** (§0.5bis #1 existant) — re-scope avec briques 1-6.
3. **HTF_Bias_15m_BOS_v2 TRUE HTF** — reprise du meilleur candidat PARTIAL_IMPL déjà observé (QQQ SHORT +0.076).
4. **NWOG_v1** (New Week Opening Gap, MASTER+TRUE convergents) — MASTER couvre, briques similaires à #1.
5. **Daily_Profiles_Filter overlay** (MASTER seul) — top-layer filtre, testable cheap.

### 6.5 Décision hypothèse A vs B

**Hypothèse A ("MASTER mal codé") est dominante, supportée empiriquement par la matrix** :
- **22/30 FANTASY + 5 PARTIAL_IMPL = 27/30 verdicts négatifs NE testent PAS le canon MASTER+TRUE honnêtement**.
- **Seuls 3/30 verdicts sont falsifiants du canon** (Stat_Arb v1+v2 non-ICT + Morning_Trap user KILL terminal) — et 2/3 sont non-ICT donc hors périmètre canon.
- **Le bot n'a jamais vraiment implémenté SMT cross-index HTF-anchored, pool freshness, EQ most-recent, ni bias 7-step**. 10 data points négatifs sont donc **cohérents avec "ICT mal codé"**, pas avec "ICT arbitré".
- **Mais hypothèse B reste testable** : si `HTF_Bias_15m_BOS_v2` + `SMT_SPY_QQQ_v1` + `Aplus_01_v2 TRUE HTF` **tous les trois** échouent avec briques canon complètes (Stage 2 E[R]_pre_reconcile > 0.197R/trade), alors B sera empiriquement renforcée et le framework ICT sera insuffisant, pas juste mal codé.

**Chemin rationnel** : livrer 6 briques transversales (§6.3) → rewrite ≥ 2 playbooks (§6.1 #1 + #2 + éventuellement nouveau SMT §6.4 #1) → 3 data points convergents. Si tous passent gates §0.6 Stage 1-2, A validée. Si tous échouent, B renforcée et pivot plan (§0.3 point 3 déjà déclenché post-Leg 4.2, escalation user en cours).

---

## 7. Rapport final (≤ 500 mots)

**Stats matrix** (30 playbooks) :
- **0 ALIGNED_TRUE_MASTER**
- **5 PARTIAL_IMPL** : Aplus_01_full_v1, Aplus_02_Premarket_v1, HTF_Bias_15m_BOS, Aplus_03_v2, Aplus_04_v2 α''/ε
- **22 FANTASY** (vocab-borrowing sans mécaniques canon)
- **3 OBSOLETE** (hypothèse réfutée multi-fois : Aplus_03 R.3, Aplus_04 v2, IFVG isolé)
- **8 STRUCTURAL_KILL** (Stat_Arb v1+v2, ORB, Lunch, VWAP_Bounce, EMA/RSI baseline, FVG_Scalp_1m, DAY/SCALP SPAM, Morning_Trap user KILL)

**Top 5 gaps briques systémiques** :
1. **SMT cross-index HTF-anchored** absent (`detect_smt` existant = rolling max/min 1h non-anchored, scoring bonus seul)
2. **`tp_resolver` freshness filter + pool_tf 4H/1H** absent (α'' schema existe mais sur pools 5m)
3. **HTF bias state machine 7-step** absent (SMA_5 proxy 0/171 rejections Phase D.1)
4. **Equilibrium most-recent swing** absent (`equilibrium.py` utilise extrêmes absolus lookback 20)
5. **Macro kill zone 9:50-10:10 + 13:50-14:10** absent + **3 daily profiles filter** absent

**Verdict hypothèse A vs B** : **A DOMINANTE**. 27/30 (90 %) verdicts négatifs NE testent PAS le canon. Seuls 3 playbooks = verdict falsifiant (2 non-ICT Stat_Arb + 1 user KILL). Les 10 data points négatifs cross-playbook 2025 SPY/QQQ sont **cohérents avec "ICT mal codé"** (SMA proxy, fixed RR peak_R<1R, pools 5m/15m sans freshness, SMT scoring-only) — pas "ICT arbitré". Mais B reste testable si rewrites faithful échouent.

**Top 3 recommandations amendements §0.5bis** :

1. **INSERT NEW #0 briques transversales** (~10-12j dev) AVANT tout rewrite individuel : SMT HTF-anchored + tp_resolver freshness 4H/1H + structure_k9 bias + EQ most-recent + macro kill zone + 3 daily profiles. Sans ces briques, tout rewrite FANTASY se reproduit. Gate pré-backlog §0.7 G4 (verdict templating) + proposer **G6 briques canon transversales** comme pré-requis bloquant au §0.5bis.

2. **INSERT NEW #1.5 SMT_Divergence_SPY_QQQ_v1** avant #1 Aplus_01 v2. Justification : (a) MASTER+TRUE convergents 100 %, (b) QUANT neutre (aucune décote académique), (c) structurellement novel (0/30 utilise dual-asset gate), (d) briques 50 % en place (PairSpreadTracker Sprint 3 réutilisable), (e) infra plus légère qu'Aplus_01 v2 cascade. Candidat **plus haute probabilité** de produire un 1er data point positif canon-faithful.

3. **AMEND #1 Aplus_01_v2 TRUE HTF enrichi → scope élargi** : bias 7-step via structure_k9 (QUANT EuFakzlBLOA), EQ most-recent (TRUE wzq2AMsoJKY), SMT gate (TRUE+MASTER convergent), macro kill zone 9:50-10:10 (MASTER seul), pool_tf 4H+freshness (TRUE pKIo-aVic-c). Réouverture légitime §10 r11 sous condition briques #0 livrées. **Subsume également rewrite HTF_Bias_15m_BOS_v2** (2e candidat signalé matrix) comme variante Family B du même playbook enrichi.

**Fin Phase IV.** Passage Phase V `05_PLAN_DECISION.md` avec input A/B décision + §0.5bis amendements + §6.3 briques ordering.
