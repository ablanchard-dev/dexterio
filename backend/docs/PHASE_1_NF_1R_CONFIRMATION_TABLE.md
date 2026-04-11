# PHASE 1 — Tableau confirmation News_Fade 1.0R

| campaign | label | trades | WR% | ΣR | E[R] | %TP | %SL | %session_end | durée méd min |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| PHASE_B_REFERENCE | nov2025_agg_4w | 27 | 59.3 | 1.48 | 0.055 | 33.3 | 3.7 | 63.0 | 36.0 |
| nf1r_confirm_aug2025 | 202508_w01 | 0 | 0.0 | 0.00 | 0.000 | 0.0 | 0.0 | 0.0 | n/a |
| nf1r_confirm_aug2025 | 202508_w02 | 11 | 9.1 | -0.70 | -0.064 | 0.0 | 0.0 | 100.0 | 46.0 |
| nf1r_confirm_aug2025 | 202508_w03 | 7 | 85.7 | 1.44 | 0.205 | 85.7 | 0.0 | 14.3 | 54.0 |
| nf1r_confirm_aug2025 | 202508_w04 | 7 | 0.0 | -0.85 | -0.122 | 0.0 | 0.0 | 100.0 | 11.0 |
| nf1r_confirm_oct2025 | 202510_w01 | 2 | 0.0 | -0.06 | -0.030 | 0.0 | 0.0 | 100.0 | 26.0 |
| nf1r_confirm_oct2025 | 202510_w02 | 16 | 18.8 | -0.84 | -0.052 | 0.0 | 0.0 | 100.0 | 56.0 |
| nf1r_confirm_oct2025 | 202510_w03 | 8 | 0.0 | -0.97 | -0.121 | 0.0 | 0.0 | 100.0 | 76.0 |
| nf1r_confirm_oct2025 | 202510_w04 | 0 | 0.0 | 0.00 | 0.000 | 0.0 | 0.0 | 0.0 | n/a |
| nf1r_confirm_sep2025 | 202509_w01 | 7 | 0.0 | -0.70 | -0.101 | 0.0 | 0.0 | 100.0 | 6.0 |
| nf1r_confirm_sep2025 | 202509_w02 | 0 | 0.0 | 0.00 | 0.000 | 0.0 | 0.0 | 0.0 | n/a |
| nf1r_confirm_sep2025 | 202509_w03 | 18 | 27.8 | -0.88 | -0.049 | 0.0 | 5.6 | 94.4 | 63.5 |
| nf1r_confirm_sep2025 | 202509_w04 | 9 | 0.0 | -0.65 | -0.072 | 0.0 | 0.0 | 100.0 | 16.0 |

## exit_reason (détail)
- **PHASE_B_REFERENCE / nov2025_agg_4w** : `{'session_end': 17, 'TP1': 9, 'SL': 1}`
- **nf1r_confirm_aug2025 / 202508_w01** : `{}`
- **nf1r_confirm_aug2025 / 202508_w02** : `{'session_end': 11}`
- **nf1r_confirm_aug2025 / 202508_w03** : `{'TP1': 6, 'session_end': 1}`
- **nf1r_confirm_aug2025 / 202508_w04** : `{'session_end': 7}`
- **nf1r_confirm_oct2025 / 202510_w01** : `{'session_end': 2}`
- **nf1r_confirm_oct2025 / 202510_w02** : `{'session_end': 16}`
- **nf1r_confirm_oct2025 / 202510_w03** : `{'session_end': 8}`
- **nf1r_confirm_oct2025 / 202510_w04** : `{}`
- **nf1r_confirm_sep2025 / 202509_w01** : `{'session_end': 7}`
- **nf1r_confirm_sep2025 / 202509_w02** : `{}`
- **nf1r_confirm_sep2025 / 202509_w03** : `{'session_end': 17, 'SL': 1}`
- **nf1r_confirm_sep2025 / 202509_w04** : `{'session_end': 9}`

## Agrégats par campagne

| campaign | semaines | NF trades | ΣR NF | E[R] NF | mean %TP | mean %session_end |
|---|---:|---:|---:|---:|---:|---:|
| nf1r_confirm_aug2025 | 4 | 25 | -0.12 | -0.0049 | 21.43 | 53.57 |
| nf1r_confirm_oct2025 | 4 | 26 | -1.86 | -0.0716 | 0.0 | 75.0 |
| nf1r_confirm_sep2025 | 4 | 34 | -2.23 | -0.0657 | 0.0 | 73.61 |

## Gate (heuristique)
- **REOPEN_1R_VS_1P5R** — expectancy NF agrégée négative (-0.0496R) vs ref PHASE B positive (0.0548R), n=85 — rouvrir arbitrage 1.0R vs 1.5R sur mêmes fenêtres

## Funnel NY / LSS (extraits summary)
- **nf1r_confirm_aug2025 / 202508_w01** NY={'matches': 0, 'setups_created': 0, 'after_risk': 0, 'trades': 0} LSS={'matches': 464, 'setups_created': 335, 'after_risk': 335, 'trades': 319}
- **nf1r_confirm_aug2025 / 202508_w02** NY={'matches': 0, 'setups_created': 0, 'after_risk': 0, 'trades': 0} LSS={'matches': 425, 'setups_created': 334, 'after_risk': 334, 'trades': 313}
- **nf1r_confirm_aug2025 / 202508_w03** NY={'matches': 0, 'setups_created': 0, 'after_risk': 0, 'trades': 0} LSS={'matches': 461, 'setups_created': 336, 'after_risk': 336, 'trades': 316}
- **nf1r_confirm_aug2025 / 202508_w04** NY={'matches': 362, 'setups_created': 269, 'after_risk': 269, 'trades': 10} LSS={'matches': 423, 'setups_created': 307, 'after_risk': 307, 'trades': 225}
- **nf1r_confirm_oct2025 / 202510_w01** NY={'matches': 0, 'setups_created': 0, 'after_risk': 0, 'trades': 0} LSS={'matches': 381, 'setups_created': 277, 'after_risk': 277, 'trades': 265}
- **nf1r_confirm_oct2025 / 202510_w02** NY={'matches': 0, 'setups_created': 0, 'after_risk': 0, 'trades': 0} LSS={'matches': 355, 'setups_created': 249, 'after_risk': 249, 'trades': 215}
- **nf1r_confirm_oct2025 / 202510_w03** NY={'matches': 0, 'setups_created': 0, 'after_risk': 0, 'trades': 0} LSS={'matches': 482, 'setups_created': 344, 'after_risk': 344, 'trades': 313}
- **nf1r_confirm_oct2025 / 202510_w04** NY={'matches': 0, 'setups_created': 0, 'after_risk': 0, 'trades': 0} LSS={'matches': 417, 'setups_created': 277, 'after_risk': 277, 'trades': 269}
- **nf1r_confirm_sep2025 / 202509_w01** NY={'matches': 1, 'setups_created': 1, 'after_risk': 1, 'trades': 0} LSS={'matches': 349, 'setups_created': 238, 'after_risk': 238, 'trades': 200}
- **nf1r_confirm_sep2025 / 202509_w02** NY={'matches': 361, 'setups_created': 238, 'after_risk': 238, 'trades': 10} LSS={'matches': 496, 'setups_created': 331, 'after_risk': 331, 'trades': 282}
- **nf1r_confirm_sep2025 / 202509_w03** NY={'matches': 103, 'setups_created': 79, 'after_risk': 79, 'trades': 0} LSS={'matches': 465, 'setups_created': 358, 'after_risk': 358, 'trades': 326}
- **nf1r_confirm_sep2025 / 202509_w04** NY={'matches': 94, 'setups_created': 70, 'after_risk': 70, 'trades': 0} LSS={'matches': 418, 'setups_created': 306, 'after_risk': 306, 'trades': 284}