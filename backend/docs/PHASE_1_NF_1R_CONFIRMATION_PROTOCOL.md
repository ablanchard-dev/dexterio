# PHASE 1 — Protocole de confirmation News_Fade 1.0R (multi-fenêtres)

## Documents relus (inventaire)

| Document | Rôle |
|----------|------|
| `PHASE_A_NF_STOP_DECISION.md` | Stop NF OPTION A (±0,5 % moteur) |
| `PHASE_B_NF_TP1_RR_SWEEP.md` | Sweep tp1_rr ; preuve NY/LSS stable si seul NF change |
| `PHASE_C_NF_TP1_RR_1P0_PROVISIONAL.md` | Adoption YAML 1.0R provisoire + plan validation |
| `AUDIT_NEWS_FADE_SESSION_END.md` | Ordre TP vs session_end (NF) |
| `AUDIT_NEWS_FADE_INTRABAR.md` | Lecture prix / intrabar |
| `AUDIT_NEWS_FADE_GEOMETRY.md` | Géométrie SL/TP |
| `AUDIT_NEWS_FADE_GEOMETRY_REVALIDATION_NOV2025.md` | Revalidation post-fix |

## Protocole (identique au mini-lab standard)

- **Runner** : `scripts/run_mini_lab_week.py` (aucun `--playbooks-yaml` → YAML canonique, NF 1.0R post–PHASE C).
- **Risk / LSS** : défauts actuels (`respect_allowlists`, bypass quarantaine LSS) inchangés.
- **Symboles** : `SPY,QQQ`.
- **Sorties** : `--output-parent nf1r_confirm_<mois>` pour ne **pas** écraser `results/labs/mini_week/<label>/` (baseline historique).
- **Run ID** : `miniweek_nf1r_confirm_<campagne>_<label>`.

## Presets multi-semaines

`scripts/run_mini_lab_multiweek.py` expose :

- `sep2025`, `oct2025`, `aug2025`, `nov2025` (4 fenêtres chacun).
- `--output-parent nf1r_confirm_sep2025` (exemple) transmis à chaque sous-run.

### Commandes (exemples)

```bash
cd backend

# Septembre entier (4 semaines), campagne dédiée
.venv/bin/python scripts/run_mini_lab_multiweek.py \
  --preset sep2025 \
  --output-parent nf1r_confirm_sep2025 \
  --skip-existing \
  --no-aggregate

# Octobre
.venv/bin/python scripts/run_mini_lab_multiweek.py \
  --preset oct2025 \
  --output-parent nf1r_confirm_oct2025 \
  --skip-existing \
  --no-aggregate

# Août
.venv/bin/python scripts/run_mini_lab_multiweek.py \
  --preset aug2025 \
  --output-parent nf1r_confirm_aug2025 \
  --skip-existing \
  --no-aggregate
```

**Dossiers attendus** : `results/labs/mini_week/nf1r_confirm_<mois>/<YYYYMM_w0x>/`

Artefacts par fenêtre : `mini_lab_summary_<label>.json`, `trades_miniweek_<run_id>_AGGRESSIVE_DAILY_SCALP.parquet`, `debug_counts_*.json`, etc.

## Agrégation

```bash
cd backend
.venv/bin/python scripts/aggregate_nf_1r_confirmation.py \
  --out-md docs/PHASE_1_NF_1R_CONFIRMATION_TABLE.md
```

Sorties :

- `results/labs/mini_week/_nf_1r_confirmation_aggregate.json`
- `docs/PHASE_1_NF_1R_CONFIRMATION_TABLE.md` (option `--out-md`)

La ligne **PHASE_B_REFERENCE** reprend l’agrégat **4 semaines** nov2025 @ tp1=1.0 depuis `_phase_b_nf_tp1_aggregate.json` (sweep `phase_b_nf_tp1rr_1p00`).

## Garde-fous NY / LSS

- **Même semaine calendaire, seul NF change** : preuve structurée en PHASE B (funnel NY/LSS identiques entre variantes tp1).
- **Mois différents** : les **nombres absolus** NY/LSS **varient** avec le marché ; la validation est **absence de régression YAML** (NY/LSS non modifiés dans le fichier) + cohérence moteur. Comparer le funnel NY d’une fenêtre **confirm** à une **re-run baseline impossible sans ancien YAML** ; en pratique : vérifier que les champs funnel restent peuplés de façon cohérente et qu’aucun patch NF n’a touché `NY_Open_Reversal` dans `playbooks.yml`.

## Critères de décision (gate)

| Situation | Gate |
|-----------|------|
| Moins de 2 mois complets (≥4 semaines / mois) agrégés | **KEEP_1R_PROVISIONAL** |
| ≥2 mois ; expectancy NF et ΣR du même ordre que nov2025 @1R ; %TP reste matériel | **PROMOTE_1R_TO_PAPER_CANDIDATE** (supervisé) |
| ≥2 mois ; dégradation forte et stable (ex. expectancy très négative, 0 TP1 récurrent) vs nov | **REOPEN_1R_VS_1P5R** |

**Preuve actuelle (2026-04-11)** : `nf1r_confirm_sep2025/202509_w01` exécuté ; **n = 7** trades NF — **échantillon trop petit** pour REOPEN ; profil extrême (100 % `session_end`) → **compléter** w02–w04 sep + oct + aug avant gate finale.

## Gate courante

**KEEP_1R_PROVISIONAL** — infrastructure et premier run réel hors nov2025 livrés ; confirmation statistique multi-mois **en cours / à poursuivre** selon commandes ci-dessus.
