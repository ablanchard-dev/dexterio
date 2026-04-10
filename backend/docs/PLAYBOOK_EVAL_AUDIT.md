# Audit playbooks (sans casser le mode prod)

Le comportement **par défaut** (allowlist, denylist, kill-switch, caps) reste inchangé si aucune variable d’environnement n’est définie.

## Variables d’évaluation (backtests uniquement)

| Variable | Effet |
|----------|--------|
| `RISK_EVAL_ALLOW_ALL_PLAYBOOKS=true` | Autorise tous les playbooks (ignore allowlist/denylist). |
| `RISK_EVAL_RELAX_CAPS=true` | Désactive cooldown, caps journaliers, circuit breakers “quotidiens”, quota A+ par jour. |
| `RISK_EVAL_DISABLE_KILL_SWITCH=true` | Ne désactive **aucun** playbook en cours de run (stats complètes sur toute la période). |

Exemple PowerShell (depuis `backend/`) :

```powershell
$env:RISK_EVAL_ALLOW_ALL_PLAYBOOKS='true'
$env:RISK_EVAL_RELAX_CAPS='true'
$env:RISK_EVAL_DISABLE_KILL_SWITCH='true'
python -c "..."  # ton BacktestConfig
```

**Ne pas** activer ces flags en production / live trading.

## Données et bougies (backtest)

- Le moteur de backtest lit les **Parquet M1** (`pd.read_parquet`), normalise `datetime` en **UTC**, et construit des `Candle` OHLCV.
- La qualité “prix réel” dépend **uniquement** de la source utilisée pour **générer** ces fichiers (broker, fournisseur, ajustements splits/dividendes, timezone).
- `engines/data_feed.py` (yfinance) sert surtout au **fetch live / hors backtest** ; ce n’est pas la même chaîne que le rejeu Parquet.

Pour valider l’ingestion : `python backend/utils/path_resolver.py`, puis contrôler un échantillon de lignes (pas de trous anormaux, OHLC cohérents, volume).

## Affiner les playbooks sans tout casser

1. Enrichir `playbooks.yml` (contexte, timefilters, seuils de scoring) **par petits patches** avec un run de comparaison avant/après.
2. Utiliser l’audit ci-dessus pour classer les playbooks sur une période longue.
3. Garder prod avec allowlist/denylist actuelles jusqu’à ce qu’un playbook repasse les critères sur plusieurs fenêtres.
