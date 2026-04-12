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

# Manifest de complétude seul (scan disque)
.venv/bin/python scripts/refresh_nf_tp1_arbitration_manifest.py

# Agrégation + tableau (+ réécrit le manifest)
.venv/bin/python scripts/aggregate_nf_tp1_arbitration.py \
  --out-json results/labs/mini_week/_nf_tp1_arbitration_aggregate.json \
  --out-md docs/PHASE_NF_TP1_ARBITRATION_TABLE.md
```

## Manifest de campagne (complétude)

- **Fichier** : `results/labs/mini_week/_nf_tp1_arbitration_campaign_manifest.json`
- **Spécification des 12 paires** : `utils/nf_tp1_arbitration_campaign.py` (`NF_TP1_ARBITRATION_WINDOWS` — à garder aligné avec `run_mini_lab_multiweek.PRESETS` pour aug/sep/oct).
- Contenu : liste attendue, `pairs_complete`, `pairs_missing`, `global_status` (`NOT_STARTED` | `IN_PROGRESS` | `COMPLETE_OK`).

## Alignement du nombre de trades NF (évolution)

**Pourquoi l’égalité stricte existait** : hypothèse « mêmes entrées, seul le TP1 change » → même cardinal de trades **News_Fade** ; éviter de comparer E[R]/ΣR sur des **cohortes de tailles différentes** (biais de composition).

**Pourquoi ce n’est plus un blocage dur** : en pratique le moteur peut produire de **petits écarts** (ordre d’exécution, risk, effets de bord session). L’agrégateur calcule maintenant `trade_count_alignment` (`aligned` / `minor` / `moderate` / `major`) avec **notes** ; des niveaux `moderate` ou `major` alimentent **`decision.warnings`** sans invalider automatiquement `KEEP_1P0R` / `SWITCH_TO_1P5R`. Interprétation prudente si `major`.

## Seuil ε (`epsilon_er`, défaut 0.015R)

**Nature** : seuil **opérationnel heuristique** — pas intervalle de confiance, pas test d’hypothèse formel sur E[R].

**Logique métier** : exiger un écart **net** entre les deux bras après agrégation sur **12 semaines**, plutôt que trancher sur des différences du même ordre que le **bruit de petits sous-échantillons** hebdomadaires.

**Ancrage factuel (repo)** : sur PHASE B nov (`_phase_b_nf_tp1_aggregate.json`), l’écart d’expectancy entre tp1=1.0 et tp1=1.5 sur **27** trades NF est ~**4·10⁻⁴R**, donc **très** inférieur à 0.015R : le seuil vise une séparation **structurelle** sur la campagne multi-semaines, pas le micro-raffinement d’un seul mois.

**Où c’est documenté** : ce fichier ; recopie technique dans `decision.epsilon_er_rationale` (JSON agrégat) et constante `EPSILON_ER_RATIONALE` dans `scripts/aggregate_nf_tp1_arbitration.py`. Surcharge possible : `aggregate_nf_tp1_arbitration.py --epsilon-er <valeur>`.

## Décision (implémentée)

Seuil **ε** (défaut **0.015R**) sur **ΔE[R] = E[R]_1.5 − E[R]_1.0** (global, 12 fenêtres appariées), avec **ΣR** cohérent :

| Code | Condition (schéma) |
|------|---------------------|
| **SWITCH_TO_1P5R** | ΔE[R] ≥ ε et ΣR_1.5 > ΣR_1.0 |
| **KEEP_1P0R** | ΔE[R] ≤ −ε et ΣR_1.5 < ΣR_1.0 |
| **KEEP_BOTH_UNRESOLVED_PENDING_MORE_DATA** | sinon ; ou **≠ 12** paires complètes ; ou \|ΔE[R]\| < ε ; ou contradiction ΔE[R] vs ΔΣR |

## Mise à jour YAML canonique

- **SWITCH_TO_1P5R** : `News_Fade.take_profit_logic.min_rr` et `tp1_rr` → **1.5** (seul NF ; NY inchangé).
- **KEEP_1P0R** : idem → **1.0**.
- **UNRESOLVED** : pas de changement canonique forcé.

## Artefacts

- Manifest : `results/labs/mini_week/_nf_tp1_arbitration_campaign_manifest.json`
- JSON agrégat : `results/labs/mini_week/_nf_tp1_arbitration_aggregate.json`
- MD : `docs/PHASE_NF_TP1_ARBITRATION_TABLE.md` (après agrégation)

## Décision finalisée (post-run)

Après `aggregate_nf_tp1_arbitration.py`, la décision est dans **`decision.decision`** et la justification dans **`decision.reason`**. Recopier ici la ligne verdict + mettre à jour le YAML canonique NF **uniquement** si le code est `KEEP_1P0R` ou `SWITCH_TO_1P5R` (voir section « Mise à jour YAML canonique »).
