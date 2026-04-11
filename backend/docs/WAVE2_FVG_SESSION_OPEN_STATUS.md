# Wave 2 — Statut FVG_Fill_Scalp & Session_Open_Scalp (mis à jour)

## FVG_Fill_Scalp — patch **W2-1** (YAML uniquement)

### Preuve goulot (avant patch)

| Source | semaine | matches FVG | setups | trades FVG |
|--------|---------|------------:|-------:|-----------:|
| `nf1r_confirm_sep2025/202509_w01/mini_lab_summary_*.json` | sep w01 | **0** | 0 | 0 |
| `mini_week/202511_w01/mini_lab_summary_*.json` | nov w01 | 67 | 67 | 17 |

Hypothèse validée : **filtre contexte `day_type=trend` + structure sans `range`** excluait largement la semaine testée.

### Patch minimal

- Fichier : `knowledge/playbooks.yml`, playbook **FVG_Fill_Scalp** seul.
- Changement : `day_type_allowed: ["trend", "range"]`, `structure_htf: [..., "range"]`.
- **NY / News_Fade** : non modifiés.

### Preuve RUN (après patch)

- Commande :  
  `run_mini_lab_week.py --start 2025-09-01 --end 2025-09-07 --label 202509_w01 --output-parent wave2_fvg_w21_validate`
- Résultat funnel **FVG** : **matches 213**, **setups 77**, **trades 32** (même fenêtre que preuve « 0 »).
- Funnel **NY_Open_Reversal** : inchangé vs preuve sep w01 précédente (1 / 1 / 1 / 0 trades).

### Test

- `tests/test_wave2_fvg_fill_scalp_w21_yaml.py` — charge `PlaybookLoader` et assert `range` présent.

### Verdict FVG

**READY_WITH_LIMITATIONS** — funnel et trades **non nuls** sur semaine de référence ; étendre à 2–4 semaines supplémentaires avant « READY » sans réserves.

---

## Session_Open_Scalp

- **Aucun patch** dans cette séquence (priorité FVG respectée).
- Preuve existante : trades > 0 sur mini-labs nov w01 et sep w01 (voir historiques `mini_lab_summary`).

### Verdict Session_Open

**READY_WITH_LIMITATIONS** (inchangé).

---

## NEXT

1. Mini-labs FVG sur **oct w01** + **aug w01** avec même `output-parent` pattern `wave2_fvg_w21_*` si besoin de stabilité multi-mois.
2. Si FVG trop bruyant : assouplir **un seul** autre levier (scoring ou famille chandelles), jamais NY.
