# Roadmap portefeuille SAFE / FULL (état réel, sans activation massive)

Référence **D27** : allowlists / quarantaines dans `risk_engine.py` ; pas d’élargissement arbitraire.

## Avancées réelles (après phases 1–5)

- **News_Fade** : YAML **1.0R** (PHASE C) ; sweep PHASE B nov favorable ; **confirmation 12 semaines** aug+sep+oct (`nf1r_confirm_*`) → gate automatique **`REOPEN_1R_VS_1P5R`** (E[R] agrégée négative vs ref nov @1R, n=85). Voir `_nf_1r_confirmation_aggregate.json`.
- **FVG_Fill_Scalp** : patch **W2-1** (range autorisé) ; preuve RUN sep w01 **213 matches / 32 trades** vs **0** avant ; test `test_wave2_fvg_fill_scalp_w21_yaml.py`.
- **Session_Open_Scalp** : **READY_WITH_LIMITATIONS** (pas de patch supplémentaire ici).
- **Paper backend** : **`PAPER_READY_SUPERVISED_HARDENED`** (`run_manifest.json` + Pydantic).
- **Contrats** : `RunSummaryV0` + `CampaignManifestV0` validés en tests.

## Quatre paniers

### CORE_PAPER_NOW

- **Logique** : noyau AGGRESSIVE **supervisé** ; NF **après** arbitrage tp1 (sweep 1.0 vs 1.5 sur les **12 fenêtres** de confirmation).
- **Preuves** : `CORE_PAPER_NOW_LAUNCH.md`, agrégats `nf1r_confirm_*`, manifest par run.
- **Blockers** : décision **tp1** NF ; stabilité FVG W2-1 sur >1 semaine si exigé produit.
- **Condition d’entrée** : gate NF ≠ REOPEN **ou** décision explicite produit après sweep.

### NEXT_WAVE_PAPER

- **Logique** : affiner FVG (second levier si besoin) ; Session_Open si caps/concurrence à traiter.
- **Preuves** : `WAVE2_FVG_SESSION_OPEN_STATUS.md`, `WAVE2_PLAN_*`.
- **Blockers** : volume FVG trop bruyant post W2-1.
- **Condition d’entrée** : labs 2–4 semaines FVG post-patch.

### FUTURE_SAFE

- **Logique** : sous-ensemble SAFE + `SAFE_ALLOWLIST` non vide cohérent.
- **Blockers** : définition produit + perf SAFE.
- **Condition d’entrée** : décision produit dédiée.

### FUTURE_FULL

- **Logique** : allowlist large (15–20 pb) — **non ciblé**.
- **Blockers** : CORE_PAPER stable + risque live.

## DÉCISION

Priorité : **(1)** sweep **tp1 NF** sur fenêtres `nf1r_confirm_*`, **(2)** campagne `paper_supervised_*` avec manifest, **(3)** pas d’activation SAFE/FULL large.

## NEXT STEP

1. Script sweep `tp1_rr` **1.0 vs 1.5** répliquant la grille calendaire `nf1r_confirm_*` (même méthode que PHASE B).
2. Validateur **TradeRowV0** (ligne parquet).
3. SAFE : atelier produit + mini-lab dédié.
