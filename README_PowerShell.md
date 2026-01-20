# DexterioBOT - Instructions PowerShell

## Installation

```powershell
# Backend Python
cd backend
pip install -r requirements.txt

# Vérifier patterns_config.yml contient session NY
Select-String -Path knowledge/patterns_config.yml -Pattern "NY:"
```

## Exécution Backtest Rolling

```powershell
# Lancer backtest juin 2025
python backtest/run_rolling_30d.py --month 2025-06

# Résultats générés dans backend/results/
# - summary_202506.json : synthèse setups
# - funnel_by_playbook.json : métriques funnel par playbook
# - equity_202506.parquet : courbe d'équité (si trades)
```

## Tests

```powershell
# Tests complets
pytest tests/ -q

# Tests spécifiques
pytest tests/test_required_signals_and_sessions.py -v
```

## Vérification Correctifs

### 1. Session NY dans patterns_config.yml
```powershell
Select-String -Path backend/knowledge/patterns_config.yml -Pattern "NY:" -Context 2
```

Attendu :
```
  MKT_OPEN_WINDOW: "09:30-10:00"
  NY: "09:30-16:00"
  TIMEZONE: "America/New_York"
```

### 2. Custom windows fix dans playbook_loader.py
```powershell
Select-String -Path backend/engines/playbook_loader.py -Pattern "playbook.time_windows if playbook.time_windows"
```

Attendu : Priorité time_windows du playbook

### 3. BacktestEngine collecte setups
```powershell
Select-String -Path backend/backtest/engine.py -Pattern "all_generated_setups"
```

Attendu : 2 occurrences (init + collect)

## Commandes Validation

```powershell
# Hash patterns_config.yml (doit contenir fix NY)
Get-FileHash backend\knowledge\patterns_config.yml -Algorithm SHA256

# Compilation Python
python -m compileall backend

# Tests (doit être 40/40 pass)
pytest backend/tests -q

# Run rolling juin (génère funnel)
python backend/backtest/run_rolling_30d.py --month 2025-06
```

## Artefacts Attendus

Après run_rolling_30d.py :
- `backend/results/funnel_by_playbook.json` : métriques funnel
- `backend/results/summary_202506.json` : synthèse
- Timestamps dans funnel doivent être `2025-06-XX` (pas déc 2025)

## Notes Techniques

- BacktestEngine filtre automatiquement les données au mois cible via `run_name`
- Les setups sont collectés pendant l'exécution dans `engine.all_generated_setups`
- Le funnel est construit post-run en évaluant tous les playbooks sur tous les setups générés
