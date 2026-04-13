# Market Data Truth Audit

Ce document accompagne `market_data_audit_{run_id}.json`.

## Ce qui est prouvé

- Les timestamps de marché sont ordonnés et vérifiés par symbole.
- Les duplicats et out-of-order sont comptés explicitement.
- La cohérence UTC/session est vérifiée via comparaison `timestamp_entry` vs `get_session_info`.
- La cohérence prix à l'entrée est vérifiée (`entry_price` vs close de la bougie d'entrée).
- Détection explicite de `future_data_detected`.

## Ce qui reste à confirmer

- Estimation des barres manquantes reste heuristique (gaps intra-séance).
- `fill_vs_market_reference_check` est une validation de cohérence bornée, pas une reconstruction tick-perfect.

## Comment relire l'artefact

Fichier: `backend/results/<subdir>/market_data_audit_{run_id}.json`

Sections clés:

- `symbols[]`:
  - `first_ts`, `last_ts`
  - `count_loaded`, `count_processed_reference`
  - `duplicate_timestamps_count`, `out_of_order_count`, `missing_bar_estimate`
- `utc_to_exchange_tz_check`
- `session_consistency_check.match_rate`
- `entry_vs_bar_reference_check.match_rate`
- `fill_vs_market_reference_check.match_rate`
- `future_data_detected`
- `anomalies[]`
- `pass`