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
| `NY_Open_Reversal` | **À RETIRER DE ALLOWLIST (B0.3)** | **Fair audit Phase A : E[R]=-0.21, 17 tr, WR=12% — contredit "seul noyau non-négatif". YAML intouché (règle).** |
| `News_Fade` | ALLOWLIST | Gate `REOPEN_1R_VS_1P5R` **CLOS UNRESOLVED** (2026-04-14). E[R]≈-0.05 sur aug/sep/oct. Session_end dominant (94-100%). Edge possible sur nov 2025 seulement. |
| `FVG_Fill_Scalp` | ALLOWLIST | functional_but_limited — E[R] négatif OOS |
| `Session_Open_Scalp` | ALLOWLIST | **LAB ONLY** — bloqué runtime edge (2026-04-09) |
| `Morning_Trap_Reversal` | ALLOWLIST / quarantine YAML | **CALIBRATE B1** — fair audit : 24 tr, E[R]=-0.06, avg_peak_R=+1.39 (énorme MFE non capturé) |
| `Liquidity_Sweep_Scalp` | ALLOWLIST / quarantine YAML | **CALIBRATE B1** — fair audit : 39 tr, E[R]=-0.04, time_stop 69% |
| `Engulfing_Bar_V056` | (new, Phase 5a faithful) | **CALIBRATE B1** — fair audit : 26 tr, E[R]=+0.002 (près breakeven) |
| `BOS_Scalp_1m` | legacy | **CALIBRATE B1** — fair audit : 42 tr, E[R]=-0.006, time_stop 57% |
| `ORB_Breakout_5m` | **À RETIRER DE ALLOWLIST (B0.3)** | **Fair audit : E[R]=-0.10, 16 tr, WR=25% — trop tôt pour calibrer.** |
| `London_Sweep_NY_Continuation` | **DENYLIST** | -326R. Abandon. Silencieux en fair audit (0 tr). |
| `Trend_Continuation_FVG_Retest` | **DENYLIST** | -22R. Abandon. Silencieux en fair audit (0 tr). |
| `BOS_Momentum_Scalp` | **DENYLIST** | -142R. Abandon. Silencieux en fair audit (0 tr). |
| `Power_Hour_Expansion` | **DENYLIST** | -31R. Abandon. Silencieux en fair audit (0 tr). |
| `Lunch_Range_Scalp` | DISABLED | Toxique. Abandon. Silencieux en fair audit (0 tr). |
| `DAY_Aplus_1_*` | **DENYLIST** (reconfirmé fair audit) | 2157 tr, E[R]=-0.20, total_R=-430R — confirmé destructeur. |
| `SCALP_Aplus_1_*` | **DENYLIST** (reconfirmé fair audit) | 2868 tr, E[R]=-0.045, **85% time_stop**. Volume partiellement artefact RELAX_CAPS — verdict final après B0.1. |
| `FVG_Fill_V065`, `Liquidity_Raid_V056`, `Range_FVG_V054`, `Asia_Sweep_V051`, `London_Fakeout_V066`, `OB_Retest_V004` | (Phase 5a faithful MASTER) | **SILENT fair audit (6/7 MASTER, 0 match sur 4 semaines)** — diagnostic B0.2 obligatoire avant fix |
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
- **A-Close** (en cours) : PHASE_A_VERDICT.md + CLAUDE.md sync + commit.
- **B0.1** : spam_audit.py + re-run oct_w2 caps actives / kill-switch off (isoler anti-spam).
- **B0.2** : diagnose_silent_playbooks.py + taxonomie 2 niveaux.
- **B0.3** : retirer NY_Open_Reversal + ORB_Breakout_5m de `AGGRESSIVE_ALLOWLIST` ([risk_engine.py:51-59](backend/engines/risk_engine.py#L51-L59)).
- **B0.4** : corpus calib production-like (`calib_corpus_v1/`, allowlist 5 playbooks, caps actives) — input unique de B1.
- **B1** : `calibrate_sl_tp.py` sur calib_corpus_v1 → patch YAML ciblé (4-5 playbooks max, review humaine obligatoire).
- **B2** : re-audit calibré avec caps normales + split train/test anti-overfit.

---

## Hors scope immédiat

UI · live IBKR · refonte moteur · NF TP/breakeven · Wave 2 · A+ transcripts branchement · nouvelles couches outillage
