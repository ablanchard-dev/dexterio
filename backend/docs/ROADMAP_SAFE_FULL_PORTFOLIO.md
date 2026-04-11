# Roadmap portefeuille SAFE / FULL (état réel, sans activation massive)

Référence contexte **D27** : allowlists / quarantaines documentées dans `risk_engine.py` et docs labs ; pas d’élargissement arbitraire ici.

## Avancées réelles intégrées

- **News_Fade** : stop OPTION A ; **tp1_rr = min_rr = 1.0R** (PHASE C, provisoire) ; multi-week nov2025 sweep PHASE B ; confirmation multi-mois **en cours** (`nf1r_confirm_*`).
- **FVG_Fill_Scalp** : actif certaines fenêtres ; **0 match** sur sep w01 — Wave 2 **NEEDS_SECOND_PATCH**.
- **Session_Open_Scalp** : trades observés mini-lab — **READY_WITH_LIMITATIONS**.

## Quatre paniers

### CORE_PAPER_NOW

- **Logique** : playbooks déjà **dans AGGRESSIVE_ALLOWLIST** avec preuves mini-lab récentes + NF 1.0R canonique.
- **Preuves** : `mini_lab_summary_*`, `_phase_b_nf_tp1_aggregate.json`, `nf1r_confirm_*` (en cours).
- **Blockers** : confirmation NF sur ≥2 mois pour stabiliser le réglage.
- **Condition d’entrée** : gate PHASE 1 → PROMOTE ou maintien supervisé explicite.

### NEXT_WAVE_PAPER

- **Logique** : **FVG_Fill_Scalp** après patch ciblé (setup/ICT) ; éventuellement affinage Session_Open.
- **Preuves** : plan `WAVE2_PLAN_FVG_SESSIONOPEN_NEWSFADE.md` ; statut `WAVE2_FVG_SESSION_OPEN_STATUS.md`.
- **Blockers** : diagnostic FVG sur semaines à matches nuls ; mini-lab 1j symbole unique.
- **Condition d’entrée** : `setups_created_by_playbook["FVG_Fill_Scalp"] > 0` sur run de validation.

### FUTURE_SAFE

- **Logique** : sous-ensemble **SAFE_POLICY** + allowlist SAFE (actuellement vide côté CORE rentable — voir logs risk).
- **Preuves** : audits existants ; pas de volume SAFE validé en parallèle AGGRESSIVE.
- **Blockers** : définition produit SAFE (quels playbooks, quels caps) + lab dédié.
- **Condition d’entrée** : décision produit + `SAFE_ALLOWLIST` non vide cohérent.

### FUTURE_FULL

- **Logique** : élargissement massif allowlist (15–20 playbooks) **non ciblé** par cette roadmap.
- **Preuves** : N/A (volontairement non activé).
- **Blockers** : stabilisation CORE_PAPER + Wave 2 + garde-fous live.
- **Condition d’entrée** : critères risque + perf par playbook (hors scope immédiat).

## DÉCISION

Ne **pas** activer SAFE/FULL large : priorité **CORE_PAPER_NOW** supervisé + **NEXT_WAVE_PAPER** pour FVG.

## NEXT STEP

1. Finaliser campagnes `nf1r_confirm_*` (sep/oct/aug).
2. Patch FVG minimal + test (Wave 2).
3. Schéma `RunSummaryV0` validé en CI (contrat front).
