# D27 — Audit portefeuille playbooks (`labfull_202511`)

**Run de référence :** `labfull_202511` — AGGRESSIVE, SPY+QQQ, `respect-allowlists`, bypass LSS (flag lab P2) aligné avec la validation Wave 1.  
**Sources :** `debug_counts_labfull_202511.json`, `summary_labfull_202511_AGGRESSIVE_DAILY_SCALP.json`, `playbook_stats_labfull_202511.json`, `lab_playbook_comparison_labfull_202511.json`, `setup_context_stats_labfull_202511.json`, `structural_diagnostics_labfull_202511.json`, `risk_engine_stats_labfull_202511.json`, `sanity_report_labfull_202511.json`, `playbook_triage_labfull_202511.json`, `playbook_capability_audit_labfull_202511.json`, `risk_engine.py`, `playbook_quarantine.yaml`.

**Validé produit :** cet audit est une **lecture** ; il ne modifie pas la Phase 3B.

---

## 1. Executive summary

- **13** playbooks enregistrés (`playbooks_registered_count`). Chiffres ci-dessous = **lecture stricte** de `debug_counts_labfull_202511.json` (Nov 2025, SPY+QQQ, AGGRESSIVE) — voir aussi `PHASE_4_D27_FUNNEL_labfull_202511.md`.
- **6** playbooks ont **SR > 0** (`setups_after_risk_filter_by_playbook`) : Morning_Trap_Reversal, Liquidity_Sweep_Scalp, Session_Open_Scalp, Trend_Continuation_FVG_Retest, NY_Open_Reversal, FVG_Fill_Scalp.
- **6** playbooks ont **T > 0** (`trades_opened_by_playbook`) : mêmes noms sauf conversion complète là où SR=T (Session_Open : 39/39). Total trades run : **1634** (`trades_opened_total`).
- **756** setups rejetés par mode (`setups_rejected_by_mode`) — surtout **DENYLIST** sur London, BOS, DAY_Aplus, SCALP_Aplus (voir `setups_rejected_by_mode_by_playbook` + exemples JSON).
- **News_Fade**, **Power_Hour_Expansion**, **Lunch_Range_Scalp** : **M = 0** sur cette fenêtre (absents de `matches_by_playbook`) → **DEAD** pour nov 2025, pas « 1 setup » (ancienne ligne obsolète corrigée).
- **SAFE_ALLOWLIST** : longueur **0** sur ce run (`risk_allowlist_snapshot.safe.len`).

**Implication SAFE / FULL :** SAFE ne se déduit pas proprement de ce seul lab si `SAFE_ALLOWLIST` est vide ; FULL reste **allowlist + lab** progressif.

---

## 2. Table D27 (M / S / SR / T) — **13 enregistrés uniquement**

Légende : **M** = `matches_by_playbook`, **S** = `setups_created_by_playbook`, **SR** = `setups_after_risk_filter_by_playbook`, **T** = `trades_opened_by_playbook`. Clé absente ⇒ **0**.

| playbook | M | S | SR | T | Classif. | Goulot |
|----------|--:|--:|--:|--:|----------|--------|
| NY_Open_Reversal | 579 | 436 | 436 | 43 | TRADED | SR→T (393) sélection / caps |
| Liquidity_Sweep_Scalp | 1500 | 1085 | 1085 | 863 | TRADED | SR→T (222) |
| Morning_Trap_Reversal | 1924 | 1417 | 1417 | 369 | TRADED | SR→T (1048) |
| Trend_Continuation_FVG_Retest | 440 | 440 | 440 | 249 | TRADED | SR→T (191) |
| FVG_Fill_Scalp | 236 | 236 | 236 | 71 | TRADED | SR→T (165) ; M→S (507) |
| Session_Open_Scalp | 61 | 39 | 39 | 39 | TRADED | — (SR=T) |
| London_Sweep_NY_Continuation | 580 | 580 | 0 | 0 | BLOCKED_BY_POLICY | 100% `setups_rejected_by_mode` (DENYLIST) |
| BOS_Momentum_Scalp | 196 | 196 | 0 | 0 | BLOCKED_BY_POLICY | idem |
| DAY_Aplus_1_Liquidity_Sweep_OB_Retest | 1957 | 1373 | 0 | 0 | BLOCKED_BY_POLICY | idem |
| SCALP_Aplus_1_Mini_FVG_Retest_NY_Open | 2226 | 1561 | 0 | 0 | BLOCKED_BY_POLICY | idem |
| News_Fade | 0 | 0 | 0 | 0 | DEAD (fenêtre) | Aucun match (news/contexte nov) |
| Power_Hour_Expansion | 0 | 0 | 0 | 0 | DEAD (fenêtre) | Aucun match |
| Lunch_Range_Scalp | 0 | 0 | 0 | 0 | DEAD (fenêtre) | Aucun match |

**Note :** Les playbooks hors des **13** enregistrés (ex. ORB, VWAP…) **ne figurent pas** dans ce `debug_counts` — les traiter dans un run où ils sont chargés (`labfull_202510` / YAML étendu).

---

## 3. SAFE / FULL / Wave 2 (rappel décisionnel)

- **SAFE :** sur **ce seul mois**, le parquet trades montre **NY_Open_Reversal ΣR ≈ −1.04** et **aucun** playbook avec profil « sniper elite » stable — voir **`PHASE_5_SAFE_MODE_PARQUET_PROOF.md`**. **News_Fade** : **0** match nov 2025. La shortlist SAFE produit reste **à valider multi-fenêtres**.
- **FULL :** **LSS** 863 trades mais **ΣR ≈ −27** sur nov 2025 ; expansion = **vagues + labs** (`PHASE_6_FULL_MODE.md`), pas activation massive.
- **Wave 2 :** **FVG_Fill_Scalp**, **Session_Open_Scalp**, **News_Fade** — `WAVE2_PLAN_FVG_SESSIONOPEN_NEWSFADE.md`.

---

## 4. Blocker categories (aligné `debug_counts_labfull_202511`)

- **Policy / DENYLIST :** London_Sweep_NY_Continuation, BOS_Momentum_Scalp, DAY_Aplus_*, SCALP_Aplus_* — setups créés puis **tous** rejetés par mode (`setups_rejected_by_mode_by_playbook`).
- **Funnel match→setup :** ex. LSS **1500→1085**, MTR **1924→1417**, FVG **236→236** (pas de « 0 S » pour FVG/Session sur ce run).
- **Funnel SR→trade :** NY / LSS / MTR / TC-FVG / FVG — écart SR−T dû à sélection par barre, caps, cooldown (détail dans `risk_engine` + moteur d’exécution).
- **DEAD (0 match) :** News_Fade, Power_Hour_Expansion, Lunch_Range_Scalp sur **nov 2025** uniquement.

---

## 5. Comparabilité Phase 3B

Les runs **post-3B** ne sont pas directement comparables aux agrégats NY/NF **pré-3B** sur R / exit_reason — voir `PHASE_3B_COMPARABILITY.md` (si présent dans le repo).

---

*Document généré pour versionnement D27 — pas de logique d’exécution dans ce fichier.*
