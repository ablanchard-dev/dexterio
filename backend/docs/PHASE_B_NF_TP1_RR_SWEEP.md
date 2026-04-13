# PHASE B — Sweep `tp1_rr` News_Fade (nov2025)

YAML canonique (inchangé sur disque) : `knowledge/playbooks.yml`.

## Tableau comparatif (News_Fade, 4 semaines agrégées)

| tp1_rr (=min_rr) | trades | winrate % | ΣR | expectancy R | % session_end | % TP | % SL | durée méd. (min) | médiane R (TP1) / tp1_rr |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1.0 | 27 | 59.3 | 1.48 | 0.055 | 63.0 | 33.3 | 3.7 | 36.0 | 0.233 / 0.233 |
| 1.25 | 27 | 59.3 | 1.26 | 0.047 | 81.5 | 14.8 | 3.7 | 36.0 | 0.307 / 0.245 |
| 1.5 | 27 | 59.3 | 1.49 | 0.055 | 85.2 | 11.1 | 3.7 | 38.0 | 0.383 / 0.255 |
| 2.0 | 27 | 59.3 | 1.44 | 0.053 | 96.3 | 0.0 | 3.7 | 41.0 | n/a / n/a |

### exit_reason (agrégé par variante)

- **tp1_rr=1.0** : `{'session_end': 17, 'TP1': 9, 'SL': 1}`
- **tp1_rr=1.25** : `{'session_end': 22, 'TP1': 4, 'SL': 1}`
- **tp1_rr=1.5** : `{'session_end': 23, 'TP1': 3, 'SL': 1}`
- **tp1_rr=2.0** : `{'session_end': 26, 'SL': 1}`

## Preuve NY / LSS (funnel mini_lab_summary)

- Comparaison **entre les 4 variantes** (même semaine) : le funnel `NY_Open_Reversal` doit être identique.
- Comparaison **vs baseline** `mini_week/<week>/` : idem si le YAML dérivé ne touche pas NY.

```json
{
  "canonical_playbooks_path": "/home/dexter/dexterio1-main/backend/knowledge/playbooks.yml",
  "cross_variant_ny_funnel": {
    "202511_w01": {
      "ny_funnel_identical_across_tp1_variants": true,
      "per_variant": [
        {
          "tp1_rr": 1.0,
          "funnel_slice": {
            "NY_Open_Reversal": {
              "matches": 203,
              "setups_created": 159,
              "after_risk": 159,
              "trades": 17
            },
            "Liquidity_Sweep_Scalp": {
              "matches": 397,
              "setups_created": 292,
              "after_risk": 292,
              "trades": 199
            }
          }
        },
        {
          "tp1_rr": 1.25,
          "funnel_slice": {
            "NY_Open_Reversal": {
              "matches": 203,
              "setups_created": 159,
              "after_risk": 159,
              "trades": 17
            },
            "Liquidity_Sweep_Scalp": {
              "matches": 397,
              "setups_created": 292,
              "after_risk": 292,
              "trades": 199
            }
          }
        },
        {
          "tp1_rr": 1.5,
          "funnel_slice": {
            "NY_Open_Reversal": {
              "matches": 203,
              "setups_created": 159,
              "after_risk": 159,
              "trades": 17
            },
            "Liquidity_Sweep_Scalp": {
              "matches": 397,
              "setups_created": 292,
              "after_risk": 292,
              "trades": 199
            }
          }
        },
        {
          "tp1_rr": 2.0,
          "funnel_slice": {
            "NY_Open_Reversal": {
              "matches": 203,
              "setups_created": 159,
              "after_risk": 159,
              "trades": 17
            },
            "Liquidity_Sweep_Scalp": {
              "matches": 397,
              "setups_created": 292,
              "after_risk": 292,
              "trades": 199
            }
          }
        }
      ]
    },
    "202511_w02": {
      "ny_funnel_identical_across_tp1_variants": true,
      "per_variant": [
        {
          "tp1_rr": 1.0,
          "funnel_slice": {
            "NY_Open_Reversal": {
              "matches": 102,
              "setups_created": 73,
              "after_risk": 73,
              "trades": 18
            },
            "Liquidity_Sweep_Scalp": {
              "matches": 393,
              "setups_created": 271,
              "after_risk": 271,
              "trades": 219
            }
          }
        },
        {
          "tp1_rr": 1.25,
          "funnel_slice": {
            "NY_Open_Reversal": {
              "matches": 102,
              "setups_created": 73,
              "after_risk": 73,
              "trades": 18
            },
            "Liquidity_Sweep_Scalp": {
              "matches": 393,
              "setups_created": 271,
              "after_risk": 271,
              "trades": 219
            }
          }
        },
        {
          "tp1_rr": 1.5,
          "funnel_slice": {
            "NY_Open_Reversal": {
              "matches": 102,
              "setups_created": 73,
              "after_risk": 73,
              "trades": 18
            },
            "Liquidity_Sweep_Scalp": {
              "matches": 393,
              "setups_created": 271,
              "after_risk": 271,
              "trades": 219
            }
          }
        },
        {
          "tp1_rr": 2.0,
          "funnel_slice": {
            "NY_Open_Reversal": {
              "matches": 102,
              "setups_created": 73,
              "after_risk": 73,
              "trades": 18
            },
            "Liquidity_Sweep_Scalp": {
              "matches": 393,
              "setups_created": 271,
              "after_risk": 271,
              "trades": 219
            }
          }
        }
      ]
    },
    "202511_w03": {
      "ny_funnel_identical_across_tp1_variants": true,
      "per_variant": [
        {
          "tp1_rr": 1.0,
          "funnel_slice": {
            "NY_Open_Reversal": {
              "matches": 0,
              "setups_created": 0,
              "after_risk": 0,
              "trades": 0
            },
            "Liquidity_Sweep_Scalp": {
              "matches": 401,
              "setups_created": 294,
              "after_risk": 294,
              "trades": 275
            }
          }
        },
        {
          "tp1_rr": 1.25,
          "funnel_slice": {
            "NY_Open_Reversal": {
              "matches": 0,
              "setups_created": 0,
              "after_risk": 0,
              "trades": 0
            },
            "Liquidity_Sweep_Scalp": {
              "matches": 401,
              "setups_created": 294,
              "after_risk": 294,
              "trades": 275
            }
          }
        },
        {
          "tp1_rr": 1.5,
          "funnel_slice": {
            "NY_Open_Reversal": {
              "matches": 0,
              "setups_created": 0,
              "after_risk": 0,
              "trades": 0
            },
            "Liquidity_Sweep_Scalp": {
              "matches": 401,
              "setups_created": 294,
              "after_risk": 294,
              "trades": 275
            }
          }
        },
        {
          "tp1_rr": 2.0,
          "funnel_slice": {
            "NY_Open_Reversal": {
              "matches": 0,
              "setups_created": 0,
              "after_risk": 0,
              "trades": 0
            },
            "Liquidity_Sweep_Scalp": {
              "matches": 401,
              "setups_created": 294,
              "after_risk": 294,
              "trades": 275
            }
          }
        }
      ]
    },
    "202511_w04": {
      "ny_funnel_identical_across_tp1_variants": true,
      "per_variant": [
        {
          "tp1_rr": 1.0,
          "funnel_slice": {
            "NY_Open_Reversal": {
              "matches": 28,
              "setups_created": 24,
              "after_risk": 24,
              "trades": 0
            },
            "Liquidity_Sweep_Scalp": {
              "matches": 309,
              "setups_created": 228,
              "after_risk": 228,
              "trades": 205
            }
          }
        },
        {
          "tp1_rr": 1.25,
          "funnel_slice": {
            "NY_Open_Reversal": {
              "matches": 28,
              "setups_created": 24,
              "after_risk": 24,
              "trades": 0
            },
            "Liquidity_Sweep_Scalp": {
              "matches": 309,
              "setups_created": 228,
              "after_risk": 228,
              "trades": 205
            }
          }
        },
        {
          "tp1_rr": 1.5,
          "funnel_slice": {
            "NY_Open_Reversal": {
              "matches": 28,
              "setups_created": 24,
              "after_risk": 24,
              "trades": 0
            },
            "Liquidity_Sweep_Scalp": {
              "matches": 309,
              "setups_created": 228,
              "after_risk": 228,
              "trades": 205
            }
          }
        },
        {
          "tp1_rr": 2.0,
          "funnel_slice": {
            "NY_Open_Reversal": {
              "matches": 28,
              "setups_created": 24,
              "after_risk": 24,
              "trades": 0
            },
            "Liquidity_Sweep_Scalp": {
              "matches": 309,
              "setups_created": 228,
              "after_risk": 228,
              "trades": 205
            }
          }
        }
      ]
    }
  },
  "baseline_vs_variants_NY": {
    "202511_w01": {
      "baseline_NY": {
        "matches": 203,
        "setups_created": 159,
        "after_risk": 159,
        "trades": 17
      },
      "variant_1p00_NY": {
        "matches": 203,
        "setups_created": 159,
        "after_risk": 159,
        "trades": 17
      },
      "variant_1p25_NY": {
        "matches": 203,
        "setups_created": 159,
        "after_risk": 159,
        "trades": 17
      },
      "variant_1p50_NY": {
        "matches": 203,
        "setups_created": 159,
        "after_risk": 159,
        "trades": 17
      },
      "variant_2p00_NY": {
        "matches": 203,
        "setups_created": 159,
        "after_risk": 159,
        "trades": 17
      },
      "each_variant_matches_baseline_funnel": true
    },
    "202511_w02": {
      "baseline_NY": {
        "matches": 102,
        "setups_created": 73,
        "after_risk": 73,
        "trades": 18
      },
      "variant_1p00_NY": {
        "matches": 102,
        "setups_created": 73,
        "after_risk": 73,
        "trades": 18
      },
      "variant_1p25_NY": {
        "matches": 102,
        "setups_created": 73,
        "after_risk": 73,
        "trades": 18
      },
      "variant_1p50_NY": {
        "matches": 102,
        "setups_created": 73,
        "after_risk": 73,
        "trades": 18
      },
      "variant_2p00_NY": {
        "matches": 102,
        "setups_created": 73,
        "after_risk": 73,
        "trades": 18
      },
      "each_variant_matches_baseline_funnel": true
    },
    "202511_w03": {
      "baseline_NY": {
        "matches": 0,
        "setups_created": 0,
        "after_risk": 0,
        "trades": 0
      },
      "variant_1p00_NY": {
        "matches": 0,
        "setups_created": 0,
        "after_risk": 0,
        "trades": 0
      },
      "variant_1p25_NY": {
        "matches": 0,
        "setups_created": 0,
        "after_risk": 0,
        "trades": 0
      },
      "variant_1p50_NY": {
        "matches": 0,
        "setups_created": 0,
        "after_risk": 0,
        "trades": 0
      },
      "variant_2p00_NY": {
        "matches": 0,
        "setups_created": 0,
        "after_risk": 0,
        "trades": 0
      },
      "each_variant_matches_baseline_funnel": true
    },
    "202511_w04": {
      "baseline_NY": {
        "matches": 28,
        "setups_created": 24,
        "after_risk": 24,
        "trades": 0
      },
      "variant_1p00_NY": {
        "matches": 28,
        "setups_created": 24,
        "after_risk": 24,
        "trades": 0
      },
      "variant_1p25_NY": {
        "matches": 28,
        "setups_created": 24,
        "after_risk": 24,
        "trades": 0
      },
      "variant_1p50_NY": {
        "matches": 28,
        "setups_created": 24,
        "after_risk": 24,
        "trades": 0
      },
      "variant_2p00_NY": {
        "matches": 28,
        "setups_created": 24,
        "after_risk": 24,
        "trades": 0
      },
      "each_variant_matches_baseline_funnel": true
    }
  }
}
```

### Note MFE

Le journal ne contient pas de MFE bar-by-bar. **Proxy** : médiane `r_multiple` sur sorties `TP1` vs `tp1_rr` (frais inclus : le ratio est souvent inférieur à 1).
