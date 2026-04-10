# D27 — Audit portefeuille playbooks (`labfull_202511`)

**Run de référence :** `labfull_202511` — AGGRESSIVE, SPY+QQQ, `respect-allowlists`, bypass LSS (flag lab P2) aligné avec la validation Wave 1.  
**Sources :** `debug_counts_labfull_202511.json`, `summary_labfull_202511_AGGRESSIVE_DAILY_SCALP.json`, `playbook_stats_labfull_202511.json`, `lab_playbook_comparison_labfull_202511.json`, `setup_context_stats_labfull_202511.json`, `structural_diagnostics_labfull_202511.json`, `risk_engine_stats_labfull_202511.json`, `sanity_report_labfull_202511.json`, `playbook_triage_labfull_202511.json`, `playbook_capability_audit_labfull_202511.json`, `risk_engine.py`, `playbook_quarantine.yaml`.

**Validé produit :** cet audit est une **lecture** ; il ne modifie pas la Phase 3B.

---

## 1. Executive summary

- **27** playbooks enregistrés dans le moteur (`playbooks_registered_count`). Sur Nov 2025, **3** ont des setups après filtre risk : **NY_Open_Reversal**, **Liquidity_Sweep_Scalp** (bypass quarantaine sur ce lab), **News_Fade** (1 setup).
- **2** playbooks ouvrent des trades (`trades_opened_by_playbook`) : NY (162), LSS (8) → **170** trades. **News_Fade** : 1 setup post-risk, **0** trade → goulot **après** risk (sélection `max(final_score)` par barre, caps minute, cooldown, etc.).
- **Raisons du peu de playbooks tradés :**
  1. `AGGRESSIVE_ALLOWLIST` = **6** noms → ~**576** setups filtrés (`setups_rejected_by_mode`).
  2. **Denylist + quarantaine YAML** (MTR, LSS sans bypass, etc.).
  3. **Funnel setup** : **Session_Open_Scalp** (622 matches) et **FVG_Fill_Scalp** (96 matches) → **0** `setups_created`.
  4. **SAFE** : `SAFE_ALLOWLIST` vide sur ce run + `SAFE_POLICY_DENYLIST` (ex. Session_Open).

**Implication SAFE / FULL :** SAFE ne peut pas être « 4–5 élites » uniquement à partir de ce lab sans autres jobs stats ; FULL s’étend par **allowlist ciblée + lab**, pas par activation des 27 d’un coup.

---

## 2. Table D27 (M / S / SR / T)

Légende : **M** = matches (`matches_by_playbook`), **S** = setups créés, **SR** = après risk, **T** = trades ouverts — issus de `debug_counts_labfull_202511.json`.

| playbook | M | S | SR | T | Statut principal | Blocage principal | Effort | Destination |
|----------|--:|--:|--:|--:|------------------|-------------------|--------|-------------|
| NY_Open_Reversal | 229 | 167 | 167 | 162 | TRADED | Sélection S→T (score / minute) | LOW | SAFE + FULL |
| Liquidity_Sweep_Scalp | 1544 | 8 | 8 | 8 | TRADED | Quarantaine + conversion M→S | MEDIUM | FULL (+ 3B) |
| News_Fade | 430 | 1 | 1 | 0 | SETUP_ONLY | Trade path post-risk | MEDIUM | SAFE / WAVE2 |
| FVG_Fill_Scalp | 96 | 0 | 0 | 0 | MATCH_ONLY | Funnel setup | MEDIUM | FULL / WAVE2 |
| Session_Open_Scalp | 622 | 0 | 0 | 0 | MATCH_ONLY | Funnel setup ; SAFE_POLICY_DENYLIST | MEDIUM | LAB |
| Morning_Trap_Reversal | 1934 | 498 | 0 | 0 | QUARANTINED + POLICY | Deny/quarantaine | HIGH | QUARANTINE |
| London_Sweep_NY_Continuation | 242 | 49 | 0 | 0 | BLOCKED_BY_POLICY | AGGRESSIVE_DENYLIST | HIGH | KILL |
| Trend_Continuation_FVG_Retest | 182 | 43 | 0 | 0 | BLOCKED_BY_POLICY | Denylist + quarantaine | HIGH | KILL |
| DAY_Aplus_1_Liquidity_Sweep_OB_Retest | 1967 | 53 | 0 | 0 | BLOCKED_BY_POLICY | Denylist | HIGH | KILL |
| SCALP_Aplus_1_Mini_FVG_Retest_NY_Open | 2256 | 7 | 0 | 0 | BLOCKED_BY_POLICY | Denylist + quarantaine | HIGH | KILL |
| BOS_Momentum_Scalp | 84 | 1 | 0 | 0 | BLOCKED_BY_POLICY | Denylist | HIGH | KILL |
| Power_Hour_Expansion | 92 | 3 | 0 | 0 | BLOCKED_BY_POLICY | Denylist | HIGH | KILL |
| Lunch_Range_Scalp | — | — | — | 0 | TECHNICALLY_DEAD (fenêtre) | 0 match dans `matches_by_playbook` | HIGH | KILL / UNDECIDED |
| NY_Lunch_Breakout_Reprice | 1767 | 49 | 0 | 0 | BLOCKED_BY_POLICY | Hors allowlist + quarantaine | HIGH | QUARANTINE |
| Opening_Range_Breakout_NY | 242 | 49 | 0 | 0 | BLOCKED_BY_MODE | Hors allowlist | MEDIUM | FULL (panier) |
| London_Reversal_Into_NY | 1683 | 49 | 0 | 0 | BLOCKED_BY_MODE | Hors allowlist | MEDIUM | FULL |
| PM_Trend_Continuation_2PM | 242 | 49 | 0 | 0 | BLOCKED_BY_MODE | Hors allowlist | MEDIUM | FULL |
| VWAP_Reclaim_Trend_Day | 135 | 30 | 0 | 0 | BLOCKED_BY_MODE | Hors allowlist | MEDIUM | FULL |
| Micro_Pullback_Scalp_M1 | 182 | 4 | 0 | 0 | BLOCKED_BY_MODE | Hors allowlist | MEDIUM | WAVE2 |
| IFVG_Flip_Scalp | 1544 | 5 | 0 | 0 | BLOCKED_BY_MODE | Hors allowlist | MEDIUM | WAVE2 |
| SMT_Divergence_Scalp | 1640 | 5 | 0 | 0 | BLOCKED_BY_MODE | Hors allowlist | MEDIUM | WAVE2 |
| Close_Reversion_Scalp | 1683 | 6 | 0 | 0 | BLOCKED_BY_MODE | Hors allowlist | MEDIUM | FULL |
| News_Reclaim_Scalp | 142 | 4 | 0 | 0 | BLOCKED_BY_MODE | Hors allowlist | MEDIUM | FULL |
| Opening_Drive_Continuation_SAFE | 206 | 48 | 0 | 0 | BLOCKED_BY_MODE | Hors allowlist | MEDIUM | FULL |
| VWAP_Failure_Reversal_SAFE | 1683 | 49 | 0 | 0 | BLOCKED_BY_MODE | Hors allowlist | MEDIUM | FULL |
| Midday_Compression_Break_SAFE | 1767 | 6 | 0 | 0 | BLOCKED_BY_MODE | Hors allowlist | MEDIUM | FULL |
| PowerHour_Pullback_SAFE | 211 | 5 | 0 | 0 | BLOCKED_BY_MODE | Hors allowlist | MEDIUM | FULL |

**Note :** `lab_playbook_comparison_labfull_202511.json` est un sous-ensemble orienté policy ; les chiffres pipeline ci-dessus viennent de `debug_counts`.

---

## 3. SAFE / FULL / Wave 2 (rappel décisionnel)

- **SAFE (4–5) :** **NY_Open_Reversal** (preuve lab) ; **News_Fade** seulement après preuve **trade** post-3B ; **FVG_Fill** seulement si funnel setup réparé. **LSS** : pas SAFE tant que quarantaine + perf négative lab.
- **FULL panier 15–20 :** noyau allowlist 6 + extension allowlist progressive (ORB, London reversal, VWAP, SAFE-daytrade, etc.) — **un par vague lab**, pas tout d’un coup.
- **Wave 2 prioritaire :** **FVG_Fill_Scalp**, **Session_Open_Scalp**, **News_Fade** (trade path) — plan détaillé : `WAVE2_PLAN_FVG_SESSIONOPEN_NEWSFADE.md`.

---

## 4. Blocker categories

- **Policy :** denylist + quarantaine (MTR, LSS sans bypass, TC, A+, BOS, …).
- **Mode :** hors `AGGRESSIVE_ALLOWLIST` → `filter_setups_by_mode` / risk.
- **Funnel match→setup :** Session_Open, FVG_Fill (0 S) ; Lunch (0 M).
- **Funnel setup→trade :** News_Fade (SR sans T) ; `max(final_score)` par symbole/barre ; cap 1 trade/symbole/minute.

---

## 5. Comparabilité Phase 3B

Les runs **post-3B** ne sont pas directement comparables aux agrégats NY/NF **pré-3B** sur R / exit_reason — voir `PHASE_3B_COMPARABILITY.md` (si présent dans le repo).

---

*Document généré pour versionnement D27 — pas de logique d’exécution dans ce fichier.*
