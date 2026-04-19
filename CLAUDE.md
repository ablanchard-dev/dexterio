# CLAUDE.md — DexterioBOT

Repo local : `/home/dexter/dexterio1-main`
Brief détaillé : `DEXTERIO_CANONICAL_BRIEF.md`
Map MASTER → playbooks : `MASTER_PLAYBOOK_MAP.md`

---

## Direction unique

```
backtest crédible → campagnes comparables → portefeuille discipliné → paper limité → live
```

---

## Hiérarchie sources de vérité (ordre de priorité)

1. `backend/docs/ROADMAP_DEXTERIO_TRUTH.md`
2. `backend/docs/BACKTEST_CAMPAIGN_LADDER.md`
3. `backend/engines/risk_engine.py` (ALLOWLIST / DENYLIST)
4. `backend/docs/CORE_PAPER_NOW_LAUNCH.md`
5. `backend/docs/ROADMAP_SAFE_FULL_PORTFOLIO.md`

---

## État playbooks (vérité code)

| Playbook | Statut | Verdict |
|----------|--------|---------|
| `NY_Open_Reversal` | **DENYLIST (B0.3 done 2026-04-19)** | Fair audit Phase A : E[R]=-0.21, 17 tr, WR=12% — contredit "seul noyau non-négatif". Déplacé ALLOWLIST→DENYLIST ([risk_engine.py](backend/engines/risk_engine.py)). YAML intouché (règle). |
| `News_Fade` | ALLOWLIST | Gate `REOPEN_1R_VS_1P5R` **CLOS UNRESOLVED** (2026-04-14). E[R]≈-0.05 sur aug/sep/oct. Session_end dominant (94-100%). Edge possible sur nov 2025 seulement. |
| `FVG_Fill_Scalp` | ALLOWLIST | functional_but_limited — E[R] négatif OOS |
| `Session_Open_Scalp` | ALLOWLIST | **LAB ONLY** — bloqué runtime edge (2026-04-09) |
| `Morning_Trap_Reversal` | ALLOWLIST + B1 patch + C.1 vwap_regime (2026-04-20) | **C.1 partial (2026-04-20)** : E[R] -0.147 (B1) → -0.123 (B2: BE/dur) → -0.081 (C.1: vwap_regime). WR 28%, n 32, total_R -2.59. Toujours <0 → signal-quality ceiling, ne pas empiler de filtres. |
| `Liquidity_Sweep_Scalp` | ALLOWLIST + C.1 vwap_regime (2026-04-20) | **C.1 NULL EFFECT (2026-04-20)** : E[R] -0.034 → -0.035 (n 51→50). vwap_regime cut matches 16-44%/wk mais `max_setups_per_session: 3` cap binding. Signal asymptote, ne pas empiler de filtres. |
| `Engulfing_Bar_V056` | (new, Phase 5a faithful) | **B1 REVIEW** (corpus: 34 tr, E[R]=-0.10, time_stop 53%) — proposé TP1 2.0→0.68R, LARGE_TP1_CUT flag. |
| `BOS_Scalp_1m` | legacy | **B1 HOLD** (corpus: 51 tr, E[R]=-0.11, peak_R p60=0.40R) — DURATION_ANOMALY (YAML 15m mais wins 120m) + SIGNAL_QUALITY_SUSPECT. Investiguer avant apply. |
| `ORB_Breakout_5m` | **DENYLIST (B0.3 done 2026-04-19)** | Fair audit : E[R]=-0.10, 16 tr, WR=25% — trop tôt pour calibrer. Déplacé ALLOWLIST→DENYLIST. |
| `London_Sweep_NY_Continuation` | **DENYLIST** | -326R. Abandon. Silencieux en fair audit (0 tr). |
| `Trend_Continuation_FVG_Retest` | **DENYLIST** | -22R. Abandon. Silencieux en fair audit (0 tr). |
| `BOS_Momentum_Scalp` | **DENYLIST** | -142R. Abandon. Silencieux en fair audit (0 tr). |
| `Power_Hour_Expansion` | **DENYLIST** | -31R. Abandon. Silencieux en fair audit (0 tr). |
| `Lunch_Range_Scalp` | DISABLED | Toxique. Abandon. Silencieux en fair audit (0 tr). |
| `DAY_Aplus_1_*` | **DENYLIST** (SPAM confirmé B0.1) | 2157 tr, E[R]=-0.20, total_R=-430R. **B0.1 : 99% des trades bloqués par cooldown/cap normal → SPAM, pas calibration possible.** |
| `SCALP_Aplus_1_*` | **DENYLIST** (SPAM confirmé B0.1) | 2868 tr, 85% time_stop sous RELAX_CAPS. **B0.1 : 97% bloqués sous caps normales + B0.1b normalcaps E[R] crashe -0.01→-0.14 → exclu calib.** |
| `FVG_Fill_V065`, `Range_FVG_V054`, `Liquidity_Raid_V056`, `FVG_Scalp_1m` | (Phase 5a + legacy) | **EXECUTION_LAYER_ISSUE (B0.2)** — setups matchent + passent risk filter puis **0 trades**. Bug exécution (SL invalide / size=0 / reject silencieux). Blocker MASTER alignment. |
| `Asia_Sweep_V051`, `London_Fakeout_V066`, `OB_Retest_V004` | (Phase 5a faithful MASTER) | **B0.2 classified** : Asia_Sweep=SESSION_WINDOW_MISMATCH, London_Fakeout=fonctionnel rare, OB_Retest=PATTERN_PRECONDITION_BUG — Phase C.0 |
| `IFVG_5m_Sweep`, `VWAP_Bounce_5m`, `HTF_Bias_15m_BOS` | quarantine | **PROMOTE candidates** — E[R]>0 sur 3-11 trades. Besoin plus de data, pas calibration. |
| A+ transcripts (`playbooks_Aplus_from_transcripts.yaml`) | Non chargé | **research_only** — jamais testé |

---

## Vérité campagnes OOS (core-3 SPY/QQQ jun–nov 2025)

Toutes les variantes sont négatives. E[R] de -0.027 à -0.039 selon variante.
FVG_Fill_Scalp est le principal porteur de dérive. NY survit mieux en isolation (no-FVG s1).

### Audit Phase 5 — 330 trades, 4 semaines, ALL 26 playbooks (2026-04-19)
- Portfolio: E[R]=-0.261, WR=30%. Aucune semaine positive.
- **MARGINAL: News_Fade** seul playbook E[R]>0 (+0.012, 13 trades).
- **KILL confirmé (6):** London_Sweep, Power_Hour, Trend_Cont, BOS_Momentum, DAY_Aplus_1, SCALP_Aplus_1.
- **12 playbooks DEAD (0 trades)** — daily caps consumed by toxic playbooks.
- Trailing stop quasi inactif (75p R=+0.11, trigger=0.8-1.0R).
- **Cause racine:** London_Sweep+Power_Hour = 51% des trades, pires performers, bloquent les autres.

### Phase A fair audit 4-semaines 2026-04-19 (jun_w3 + aug_w3 + oct_w2 + nov_w4)
**Détail : [PHASE_A_VERDICT.md](backend/docs/PHASE_A_VERDICT.md)** · **Table complète : [VERDICT_fair_audit_4weeks.md](backend/results/labs/mini_week/VERDICT_fair_audit_4weeks.md)**
- Fair audit avec `RISK_EVAL_ALLOW_ALL_PLAYBOOKS=true RISK_EVAL_RELAX_CAPS=true RISK_EVAL_DISABLE_KILL_SWITCH=true` : 5249 trades, E[R]=-0.108, 17/28 playbooks fire.
- **KILL (3) :** DAY_Aplus_1 (2157 tr, E[R]=-0.20), **NY_Open_Reversal (17 tr, E[R]=-0.21) ← contredit "noyau non-négatif"**, ORB_Breakout_5m (16 tr, E[R]=-0.10).
- **CALIBRATE (5, B1) :** Morning_Trap_Reversal (avg_peak_R=+1.39), Engulfing_Bar_V056 (E[R]=+0.002), BOS_Scalp_1m, Liquidity_Sweep_Scalp, SCALP_Aplus_1 (conditionnel B0.1 — 85% time_stop + volume partiellement artefact RELAX_CAPS).
- **SILENT (11)** dont 6/7 MASTER faithful (FVG_Fill_V065, Liquidity_Raid_V056, Range_FVG_V054, Asia_Sweep_V051, London_Fakeout_V066, OB_Retest_V004) → **détecteur silent, PAS famine de cap**. Diagnostic B0.2 obligatoire.
- **Enseignement central :** l'hypothèse "famine de cap = seul blocker" est **fausse**. Le problème racine est **détecteur qui ne match jamais**.
- **Artefact identifié :** `RISK_EVAL_RELAX_CAPS=true` désactive aussi le cooldown 5 min + cap 10/session/playbook ([risk_engine.py:379-380](backend/engines/risk_engine.py#L379-L380)). Volume 2868 SCALP_Aplus_1 + 2157 DAY_Aplus_1 partiellement artefact — B0.1 distinguera SPAM vs LEGITIMATE_VOLUME.

### Phase B0 findings 2026-04-19 (diagnostic structurel, 4 sous-phases)

- **B0.1 SPAM confirmé** (`spam_audit_report.md`) : SCALP_Aplus_1 97% bloqué par cooldown/cap, DAY_Aplus_1 99% bloqué. Re-run `fair_oct_w2_normalcaps` avec caps actives : SCALP_Aplus_1 E[R] -0.01→**-0.14** — "low negative" RELAX_CAPS était artefact d'averaging. Les deux **exclus de calibration**. Détails : [spam_audit_normalcaps_delta.md](backend/data/backtest_results/spam_audit_normalcaps_delta.md).
- **B0.2 EXECUTION_LAYER_ISSUE découvert** (`silent_playbooks_diagnosis.md`) : 4 playbooks (`FVG_Fill_V065`, `Range_FVG_V054`, `Liquidity_Raid_V056`, `FVG_Scalp_1m`) produisent matches + setups passent risk filter **mais 0 trades**. Bug exécution, pas détecteur. Bloque MASTER alignment. Investigation avant Phase C.
- **B0.3 opérationnel** : NY_Open_Reversal + ORB_Breakout_5m déplacés `AGGRESSIVE_ALLOWLIST` → `AGGRESSIVE_DENYLIST` avec commentaires de justification.
- **B0.4 corpus production-like** : `calib_corpus_v1/` (170 trades, 4 semaines, caps actives, allowlist restreinte 4 candidats) — tous gates passent (≥20 tr/playbook, gap_p50 ≥ cooldown). Manifest complet ([manifest.json](backend/results/labs/mini_week/calib_corpus_v1/manifest.json)).
- **B1 calibration proposée** ([calibration_report_v1.md](backend/data/backtest_results/calibration_report_v1.md)) : 3/4 targets flaggés SIGNAL_QUALITY_SUSPECT (peak_R p60 < 0.6R) — proposer des TP1 à 0.22-0.68R signale un problème signal, pas TP/SL. Seul `Morning_Trap_Reversal` safe apply (BE 1.0→2.15R, max_dur 155m). **Review humaine bloquante avant B2.**

### Phase C.0 root cause 2026-04-20 — EXECUTION_LAYER_ISSUE était un artefact d'audit

- **B0.2 verdict révisé** : les 4 playbooks (`FVG_Fill_V065`, `Range_FVG_V054`, `Liquidity_Raid_V056`, `FVG_Scalp_1m`) ne sont **PAS bug d'exécution**. Setups passent risk filter mais sont silencieusement rejetés par position-sizing à [risk_engine.py:966](backend/engines/risk_engine.py#L966) (`'Position size < 1 share after cap'`, 495 rejections en oct_w2).
- **Cause racine** : fair audit kill_switch=OFF + DAY_Aplus_1 actif → 1877 trades, cum -222R en fin de semaine → `account_balance × factor < entry_price` → `int(max_capital/entry_price) = 0` → reject.
- Détails : [c0_execution_layer_root_cause.md](backend/data/backtest_results/c0_execution_layer_root_cause.md).
- **Action** : pas de fix nécessaire. Test simple = re-run 1 semaine avec ces 4 playbooks en allowlist seuls (pas de DAY_Aplus_1) → devraient trade normalement. Ajouter compteur per-playbook au position-sizing reject (engine hardening, séparé).

### Phase B2 verdict 2026-04-20 — Morning_Trap calibration FAIL

- **Patch appliqué** : Morning_Trap_Reversal seul (BE 1.0→2.15R, max_duration_minutes 155). 3 autres targets non patchés (review B1 = signal-quality issue, pas TP/SL).
- **Re-run 4 semaines** (`b2_morningtrap_v1`, caps actives, allowlist 4 cibles, 28 playbooks loaded) — détails [b2_morningtrap_verdict.md](backend/data/backtest_results/b2_morningtrap_verdict.md).
- **Morning_Trap_Reversal** : E[R] **-0.147 → -0.123** (Δ +0.024), WR 20.6% → 25.0%, n 34→32. Direction correcte (BE plus large + max_dur étendu = winners protégés, durée capturée), **mais ne croise pas zéro**.
- **Mécanique observée** : SL share 76.5% → 71.9%, TP1 share 20.6% → 21.9% (winners passent BE plus souvent), avg |mae_r| 0.83 → 0.89 (losers absorbent plus de R avant exit — coût du trade-off).
- **Cause de l'échec** : WR 25% × avg winner ~1.3R ne couvre pas. La calibration TP/SL atteint son plafond — seul un filtre signal qui éjecte les pires setups peut bouger le cadran.
- **B2 gate** : ❌ FAIL (0/3 targets E[R]>0). Per validated Option A : pivot **Phase C.1** (filtres VWAP/volume).
- **BOS_Scalp_1m bloqué** : YAML `max_duration_minutes` silencieusement ignoré pour SCALPs hors PHASE3B_PLAYBOOKS — détails [bos_scalp_duration_anomaly.md](backend/data/backtest_results/bos_scalp_duration_anomaly.md). Calibration BOS_Scalp impossible jusqu'au fix engine.

### Phase C.1 progression 2026-04-20 — vwap_regime tests

- **C.0 (read-only diagnosis)** : EXECUTION_LAYER_ISSUE était un artefact d'audit (kill_switch OFF + DAY_Aplus_1 drainant le compte sous le seuil min-share). Pas de bug réel. Détails [c0_execution_layer_root_cause.md](backend/data/backtest_results/c0_execution_layer_root_cause.md).
- **C.1 Morning_Trap_Reversal** : `vwap_regime: true` → E[R] -0.123 → **-0.081** (Δ +0.042), WR 25 → 28%, n 32 inchangé. `max_setups_per_session: 2` cap binding — filtre swap which 2/session pairs fire. Cumulé B1→B2→C.1 : -0.147 → -0.123 → **-0.081**, jamais ≥0. Détails [c1_vwap_verdict.md](backend/data/backtest_results/c1_vwap_verdict.md).
- **C.1 Liquidity_Sweep_Scalp** : `vwap_regime: true` → E[R] -0.034 → **-0.035** (Δ -0.001), n 51 → 50. **Effet nul.** Même mécanique cap-binding (`max_setups_per_session: 3`) mais sous-ensemble vwap-aligné statistiquement indistinct. Détails [c1_lsweep_verdict.md](backend/data/backtest_results/c1_lsweep_verdict.md).
- **Enseignement** : vwap_regime n'est pas un edge universel. Quand post-entry tweaks (TP/SL/BE/duration) ET post-filter gates (vwap_regime) plafonnent, le signal est le ceiling. Stacker plus de filtres coûte du sample sans changer la math.
- **C.1 stop** : 2 data points (Morning_Trap +0.042, Liquidity_Sweep 0.0). **Décision humaine requise** avant : (A) volume_gate_ratio sur Liquidity_Sweep, (B) PHASE3B_PLAYBOOKS engine fix pour débloquer BOS_Scalp_1m, (C) escalade signal redesign / portfolio reduction.

---

## Vérité MASTER

`/home/dexter/Documents/MASTER_FINAL.txt` — 71 transcripts YouTube ICT/smart money.
**Le MASTER n'est pas 1m natif.** Framework réel : D/4H bias → 15m/5m setup → 1m exécution.
Les playbooks actuels compressent des concepts 5m en 1m → bruit et fréquence excessive.
Savoir exploitable mais non branché : IFVG 5m (Aplus_01/03), HTF+15m BOS (Aplus_04).

---

## Règles absolues

Ne jamais :
- Migrer / réécrire le framework
- Toucher `NY_Open_Reversal` YAML sans justification forte
- Toucher `paper_trading.py` sans raison explicite
- Modifier Wave 2 ou YAML NF sans gate claire
- Promouvoir un playbook sans preuve campagne
- Supposer que 1m = vérité stratégique universelle

Toujours :
- Métrique principale = `expectancy_r` (pas `final_capital`)
- Une variante YAML = un artefact versionné sous `knowledge/campaigns/` + commit
- Distinguer : preuve repo / preuve artefact / hypothèse / décision

---

## Priorités actives

**P0** — ~~Clore gate tp1 News_Fade~~ **CLOS (2026-04-14)** — UNRESOLVED.

**P1** — Phase 1 Edge Discovery — **verdict négatif (2026-04-16)**
WF 6 mois (8 playbooks) : tous négatifs. IFVG_5m_Sweep (MASTER) aussi négatif. Scoring zéro pouvoir prédictif (r=0.003).

**P1C/D** — Fixes structurels + Breakeven (2026-04-16) — **WF NÉGATIF. KILL CRITERIA ATTEINT.** 4 configs, 3200 tr, toutes négatives.

**P2** — Polygon 18 mois — **DIFFÉRÉ post-B2** (rejeté avant Phase A comme prochaine étape, voir roadmap).

**P3** ← **ACTIF (2026-04-19)** — Roadmap post-Phase A (plan : `/home/dexter/.claude/plans/parsed-nibbling-kettle.md`)
- ✓ **A-Close** (commit `9958649`) : PHASE_A_VERDICT.md + CLAUDE.md sync.
- ✓ **B0.1** (commit `38ffef3` + `a30d459`) : spam_audit.py + re-run normalcaps → SCALP/DAY Aplus SPAM confirmés.
- ✓ **B0.2** (commit `38ffef3`) : diagnose_silent_playbooks.py → **EXECUTION_LAYER_ISSUE découvert** sur 4 playbooks.
- ✓ **B0.3** (commit `38ffef3`) : NY_Open_Reversal + ORB_Breakout_5m déplacés AGGRESSIVE_ALLOWLIST → DENYLIST.
- ✓ **B0.4** (commit `a30d459`) : `calib_corpus_v1/` (170 tr, 4 semaines, gates OK).
- ✓ **B1 review humaine** (2026-04-20) : Morning_Trap apply approuvé seul, 3 autres skip (signal-quality flags). BOS_Scalp duration anomaly investiguée en parallèle ([bos_scalp_duration_anomaly.md](backend/data/backtest_results/bos_scalp_duration_anomaly.md)).
- ✓ **B2 Morning_Trap re-run** (2026-04-20) : E[R] -0.147 → -0.123, gate FAIL (ne croise pas zéro). Voir [b2_morningtrap_verdict.md](backend/data/backtest_results/b2_morningtrap_verdict.md).
- ✓ **C.0 root cause** (2026-04-20) : EXECUTION_LAYER_ISSUE = artefact audit (DAY_Aplus_1 spam drain account → silent position-size reject). Pas de fix engine nécessaire. [c0_execution_layer_root_cause.md](backend/data/backtest_results/c0_execution_layer_root_cause.md).
- ✓ **C.1 Morning_Trap vwap_regime** (2026-04-20) : E[R] -0.123 → -0.081 (Δ +0.042), WR 25%→28%, n inchangé (filtre nuance la sélection mais cap session=2 binding). Cumul B1→B2→C.1 : -0.147 → -0.081. Toujours négatif. Voir [c1_vwap_verdict.md](backend/data/backtest_results/c1_vwap_verdict.md).
- ✓ **C.1 Liquidity_Sweep_Scalp vwap_regime** (2026-04-20) : E[R] -0.034 → -0.035 (Δ -0.001), n 51→50. **Effet nul** — vwap-aligned subset statistiquement indistinct. Voir [c1_lsweep_verdict.md](backend/data/backtest_results/c1_lsweep_verdict.md).
- ⏸ **C.1 STOP — décision humaine requise** : (A) volume_gate_ratio sur Liquidity_Sweep [filtre sweep-aligned], (B) **PHASE3B_PLAYBOOKS engine fix** pour débloquer BOS_Scalp_1m calibration [recommandé — engine-correctness, scope prévisible], (C) accepter C.1 inconclusive, escalader signal redesign / portfolio reduction.

---

## Hors scope immédiat

UI · live IBKR · refonte moteur · NF TP/breakeven · Wave 2 · A+ transcripts branchement · nouvelles couches outillage
