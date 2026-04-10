# Market Structure Capabilities

Inventaire opérationnel des signaux déjà présents (sans ajout massif de features).

## Fiable

- `market_regime` propagé `Setup -> Trade -> TradeResult`.
- `structure_quality_score` disponible dans `Setup`.
- `had_liquidity_sweep` propagé jusqu'aux exports trades.
- `time_stop` SCALP validé et prouvé via `sanity_report`.
- `master_candle_debug` généré et cohérent avec `post_run_verification`.

## Partiel

- Détection sweep/BOS/FVG présente, mais sensibilité variable selon période.
- `session_slice` exploitable (via `session_label`), mais surtout NY sur le scope actuel.
- Grading pipeline techniquement complet, distribution métier encore triviale (dominance grade C).
- Diagnostics structurels enrichis (`edge_slices`) mais dominés par un seul playbook actif.

## Manquant

- Sous-ensemble SCALP non-NY réellement exécutable avec sweep sans dégrader robustesse.
- Validation robuste multi-régimes hors NY_Open_Reversal.
- Diversité de playbooks actifs avec edge prouvé sur fenêtres glissantes.

## À confirmer

- Conditions minimales exactes pour ré-ouvrir progressivement SCALP (sans floodgate).
- Seuils structure/liquidité qui restent stables sur plusieurs mois.
- Critère métier de passage `REFINE -> KEEP` pour playbooks non-NY.
