# Common Edge Framework

Objectif: un socle commun transparent, partageable entre playbooks.

## Dimensions communes

1. **Regime suitability**
   - Aujourd'hui: `market_regime` (trend/range/chop) via `SetupEngineV2._infer_market_regime`.
   - Fiabilité: **partiel** (heuristique robuste mais simple).
   - Code: `backend/engines/setup_engine_v2.py`.

2. **Structure quality**
   - Aujourd'hui: `structure_quality_score`.
   - Fiabilité: **partiel à bon**.
   - Code: `SetupEngineV2._compute_structure_quality_score`.

3. **Liquidity event quality**
   - Aujourd'hui: `had_liquidity_sweep` + confluences ICT (`sweep`, `liquidity_sweep`).
   - Fiabilité: **partiel** (dépend de la qualité détection patterns).
   - Code: `setup_engine_v2.py`, `playbook_loader.py`.

4. **Entry feasibility**
   - Aujourd'hui: niveaux prix calculés et validés (`invalid_price_levels`).
   - Fiabilité: **bon** pour cohérence runtime.
   - Code: `SetupEngineV2._calculate_price_levels`.

5. **RR net feasibility**
   - Aujourd'hui: `entry_rr` + filtre `rr_too_low`.
   - Fiabilité: **bon** pour garde-fou structurel.
   - Code: `setup_engine_v2.py`, exports trades.

6. **Session quality**
   - Aujourd'hui: `session_label`, `session_slice`, checks session consistency.
   - Fiabilité: **bon**.
   - Code: `utils/timeframes.py`, exports trades, audits.

7. **Direction quality**
   - Aujourd'hui: direction de setup + stats par direction dans learning matrix.
   - Fiabilité: **partiel** (dépend du contexte pattern).
   - Code: `SetupEngineV2._determine_direction`.

8. **Self-performance context**
   - Aujourd'hui: `learning_snapshot`, `playbook_triage`, `edge_learning_matrix`.
   - Fiabilité: **bon** pour observabilité post-run.
   - Code: scripts d'artefacts (`generate_learning_snapshot.py`, `generate_edge_truth_pack.py`).

## Commun vs spécifique playbook

- **Commun** (doit rester central):
  - régime, structure, liquidité, RR, session, direction, performance context.
- **Spécifique playbook** (doit rester local):
  - triggers exacts (`required_signals`, patterns requis),
  - logique d'entrée/sortie propre au setup.

## Usage opérationnel

- Filtre: rejeter contextes sans edge (ex: chop sans qualité, no_liquidity_event, rr_too_low).
- Scoring: pondérer les dimensions communes avant les signaux décoratifs.
- Apprentissage: lire matrices par axe pour décider KEEP/REFINE/QUARANTINE.
