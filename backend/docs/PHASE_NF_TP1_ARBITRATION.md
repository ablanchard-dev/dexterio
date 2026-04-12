# Arbitrage final News_Fade — tp1 **1.0R vs 1.5R** (aug + sep + oct 2025)

## Préambule (preuve repo)

Les campagnes historiques `nf1r_confirm_*` utilisent `playbooks_yaml: null` : le moteur charge le **YAML canonique** tel qu’il était au commit du run. Or, au commit des runs analysés, `News_Fade.take_profit_logic` était **tp1_rr / min_rr = 3.0** (voir `git show <git_sha>:backend/knowledge/playbooks.yml`).  
**Conclusion** : le préfixe `nf1r_confirm_` **ne prouve pas** une exécution à 1.0R au moteur.

Pour un arbitrage **1.0 vs 1.5** valide, on enchaîne des mini-labs avec **YAML dérivés** (`utils.phase_b_nf_tp1_yaml`) : seul `News_Fade` change ; **NY_Open_Reversal** est vérifié identique au canonique.

## Protocole (identique au mini-lab standard, YAML dérivé)

- Runner : `scripts/run_mini_lab_week.py` via `scripts/run_mini_lab_multiweek.py`
- Risk : défauts actuels (`respect_allowlists`, bypass quarantaine LSS)
- Symboles : `SPY,QQQ`
- Fenêtres : presets **aug2025, sep2025, oct2025** (4 semaines chacun) — même calendrier que `run_mini_lab_multiweek.PRESETS`
- Sorties :
  - `nf_tp1_arb_1p00_<preset>` — dérivé `playbooks_nf_tp1_1p00.yml`, `--nf-tp1-rr 1.0`
  - `nf_tp1_arb_1p50_<preset>` — dérivé `playbooks_nf_tp1_1p50.yml`, `--nf-tp1-rr 1.5`

## Commandes

```bash
cd backend

# YAML dérivés (régénérés depuis le canonique courant)
.venv/bin/python scripts/write_nf_tp1_derived_yaml.py --tp1-rr 1.0
.venv/bin/python scripts/write_nf_tp1_derived_yaml.py --tp1-rr 1.5

for preset in aug2025 sep2025 oct2025; do
  .venv/bin/python scripts/run_mini_lab_multiweek.py --preset "$preset" \
    --output-parent "nf_tp1_arb_1p00_${preset}" \
    --playbooks-yaml results/labs/mini_week/_phase_b_yamls/playbooks_nf_tp1_1p00.yml \
    --nf-tp1-rr 1.0 --skip-existing --no-aggregate

  .venv/bin/python scripts/run_mini_lab_multiweek.py --preset "$preset" \
    --output-parent "nf_tp1_arb_1p50_${preset}" \
    --playbooks-yaml results/labs/mini_week/_phase_b_yamls/playbooks_nf_tp1_1p50.yml \
    --nf-tp1-rr 1.5 --skip-existing --no-aggregate
done

# Agrégation + tableau
.venv/bin/python scripts/aggregate_nf_tp1_arbitration.py \
  --out-json results/labs/mini_week/_nf_tp1_arbitration_aggregate.json \
  --out-md docs/PHASE_NF_TP1_ARBITRATION_TABLE.md
```

## Décision (implémentée)

Seuil **ε = 0.015R** sur **ΔE[R] = E[R]_1.5 − E[R]_1.0** (global, 12 fenêtres appariées), avec **ΣR** cohérent :

| Code | Condition (schéma) |
|------|---------------------|
| **SWITCH_TO_1P5R** | ΔE[R] ≥ ε et ΣR_1.5 > ΣR_1.0 |
| **KEEP_1P0R** | ΔE[R] ≤ −ε et ΣR_1.5 < ΣR_1.0 |
| **KEEP_BOTH_UNRESOLVED_PENDING_MORE_DATA** | sinon ; ou **≠ 12** paires ; ou **trades NF** différents entre bras ; ou \|ΔE[R]\| < ε |

## Mise à jour YAML canonique

- **SWITCH_TO_1P5R** : `News_Fade.take_profit_logic.min_rr` et `tp1_rr` → **1.5** (seul NF ; NY inchangé).
- **KEEP_1P0R** : idem → **1.0**.
- **UNRESOLVED** : pas de changement canonique forcé.

## Artefacts

- JSON : `results/labs/mini_week/_nf_tp1_arbitration_aggregate.json`
- MD : `docs/PHASE_NF_TP1_ARBITRATION_TABLE.md` (après agrégation)

## Décision finalisée (post-run)

Après `aggregate_nf_tp1_arbitration.py`, la décision est dans **`decision.decision`** et la justification dans **`decision.reason`**. Recopier ici la ligne verdict + mettre à jour le YAML canonique NF **uniquement** si le code est `KEEP_1P0R` ou `SWITCH_TO_1P5R` (voir section « Mise à jour YAML canonique »).
