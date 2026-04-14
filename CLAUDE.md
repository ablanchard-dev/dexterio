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
| `NY_Open_Reversal` | ALLOWLIST | **Seul noyau actif. Ne pas toucher YAML.** |
| `News_Fade` | ALLOWLIST | Gate `REOPEN_1R_VS_1P5R` **CLOS UNRESOLVED** (2026-04-14). E[R]≈-0.05 sur aug/sep/oct. Session_end dominant (94-100%). Edge possible sur nov 2025 seulement. |
| `FVG_Fill_Scalp` | ALLOWLIST | functional_but_limited — E[R] négatif OOS |
| `Session_Open_Scalp` | ALLOWLIST | **LAB ONLY** — bloqué runtime edge (2026-04-09) |
| `Morning_Trap_Reversal` | ALLOWLIST / quarantine YAML | quarantined — -12R (lab 24m) |
| `Liquidity_Sweep_Scalp` | ALLOWLIST / quarantine YAML | quarantined — -9.8R |
| `London_Sweep_NY_Continuation` | **DENYLIST** | -326R. Abandon. |
| `Trend_Continuation_FVG_Retest` | **DENYLIST** | -22R. Abandon. |
| `BOS_Momentum_Scalp` | **DENYLIST** | -142R. Abandon. |
| `Power_Hour_Expansion` | **DENYLIST** | -31R. Abandon. |
| `Lunch_Range_Scalp` | DISABLED | Toxique. Abandon. |
| `DAY_Aplus_1_*` | **DENYLIST** | Détection défaillante → 0 trades |
| `SCALP_Aplus_1_*` | **DENYLIST** | 6 trades, 0 win, -1.4R |
| A+ transcripts (`playbooks_Aplus_from_transcripts.yaml`) | Non chargé | **research_only** — jamais testé |

---

## Vérité campagnes OOS (core-3 SPY/QQQ jun–nov 2025)

Toutes les variantes sont négatives. E[R] de -0.027 à -0.039 selon variante.
FVG_Fill_Scalp est le principal porteur de dérive. NY survit mieux en isolation (no-FVG s1).

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

**P0** — ~~Clore gate tp1 News_Fade~~ **CLOS (2026-04-14)** — UNRESOLVED. 94-100% session_end, tp1 inopérant sur aug/sep/oct 2025. E[R] négatif dans les deux bras. Voir `ROADMAP_DEXTERIO_TRUTH.md` § Gate NF tp1.

**P1** — NY_Open_Reversal isolé — **verdict NOT_READY (2026-04-14)**
WF 2 plis (aug30-nov27) : E[R] pondéré **-0.030** (1521 trades). Problème root cause = **fréquence aberrante** (44 trades/j, max 148/j). Pas de cap fréquence dans le YAML. Signal latent possible sur oct/nov (E[R]≈-0.001, PF 1.004) mais noyé. **Next** : `campaign_wf_ny_only_capped.yml` avec `max_setups_per_session: 1`.

**P1b** ← **ACTIF** — NY capped : dériver `campaign_wf_ny_only_capped.yml` + `max_setups_per_session: 1`, re-run, gate.

**P2** — Explorer IFVG 5m (Aplus_01/03)
Lire `engines/patterns/ifvg.py`, vérifier support multi-tf, prototype YAML, smoke 1 jour.

---

## Hors scope immédiat

UI · live IBKR · refonte moteur · NF TP/breakeven · Wave 2 · A+ transcripts branchement · nouvelles couches outillage
