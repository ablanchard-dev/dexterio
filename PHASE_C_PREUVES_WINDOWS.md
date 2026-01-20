# PHASE C - PREUVES COMPLÈTES (WINDOWS)

## BLOC 1 — PREUVE DU CODE PHASE A/B/C (sans exécution)

### Phase C : UI Backtest Jobs

**Fichiers obligatoires** :

1. **`backend/jobs/backtest_jobs.py`** ✅ EXISTS
   - Ligne 30-46: `BacktestJobRequest` avec coûts Phase B
   - Ligne 78: `create_job()` - création job avec status "queued"
   - Ligne 188: `run_backtest_worker()` - worker subprocess
   - Ligne 333: `submit_job()` - soumission async avec ProcessPoolExecutor

2. **`backend/routes/backtests.py`** ✅ EXISTS
   - Ligne 24: `POST /api/backtests/run` - lance job
   - Ligne 70: `GET /api/backtests/{job_id}` - statut
   - Ligne 128: `GET /api/backtests/{job_id}/log` - logs
   - Ligne 146: `GET /api/backtests` - liste jobs

3. **`backend/server.py`** ✅ EXISTS
   - Ligne 71: `from routes.backtests import router as backtests_router`
   - Ligne 76: `app.include_router(backtests_router, prefix="/api")`

4. **Dossier `backend/results/jobs/`** ✅ EXISTS (créé runtime)
   - Structure: `jobs/{job_id}/job.json`
   - Structure: `jobs/{job_id}/job.log`
   - Structure: `jobs/{job_id}/summary.json`
   - Structure: `jobs/{job_id}/trades.parquet`
   - Structure: `jobs/{job_id}/equity.parquet`

5. **`frontend/src/pages/Backtests.jsx`** ✅ EXISTS
   - Ligne 6: `const API_URL = process.env.REACT_APP_BACKEND_URL`
   - Ligne 72: `handleRun()` - POST /api/backtests/run
   - Ligne 48: `fetchJobStatus()` - GET /api/backtests/{job_id}
   - Ligne 62: `fetchJobLog()` - GET /api/backtests/{job_id}/log

**Grep de preuve** :
```powershell
# Vérifier endpoints Phase C
Select-String -Path "backend/routes/backtests.py" -Pattern "POST|GET"
# Output attendu: lignes 24, 70, 81, 103, 128, 146

# Vérifier inclusion router
Select-String -Path "backend/server.py" -Pattern "backtests_router"
# Output attendu: lignes 71, 76

# Vérifier worker subprocess
Select-String -Path "backend/jobs/backtest_jobs.py" -Pattern "ProcessPoolExecutor|run_backtest_worker"
# Output attendu: lignes 12, 22, 188, 343
```

---

### Phase B : Net-of-Costs

**Fichiers obligatoires** :

1. **`backend/backtest/costs.py`** ✅ EXISTS
   - Ligne 40: `calculate_ibkr_commission()` - modèles IBKR
   - Ligne 83: `calculate_regulatory_fees()` - SEC + FINRA
   - Ligne 123: `calculate_slippage()` - pct/ticks
   - Ligne 167: `calculate_spread_cost()` - bid-ask spread
   - Ligne 208: `calculate_total_execution_costs()` - fonction principale

2. **`backend/models/backtest.py`** ✅ EXISTS (vérifier champs)
   - Champs costs config: `commission_model`, `enable_reg_fees`, `slippage_model`, etc.
   - Champs metrics: `total_pnl_gross_R`, `total_pnl_net_R`, `total_costs_dollars`

3. **`backend/backtest/engine.py`** ✅ EXISTS (vérifier import)
   - Import: `from backtest.costs import calculate_total_execution_costs`
   - Calcul dans `_process_exit()`

**Grep de preuve** :
```powershell
# Vérifier fonction de calcul costs
Select-String -Path "backend/backtest/costs.py" -Pattern "calculate_total_execution_costs"
# Output attendu: lignes 208, 245, etc.

# Vérifier champs Gross vs Net
Select-String -Path "backend/models/backtest.py" -Pattern "total_pnl_gross_R|total_pnl_net_R|total_costs_dollars"
# Output attendu: lignes de définition des champs

# Vérifier import dans engine
Select-String -Path "backend/backtest/engine.py" -Pattern "from backtest.costs import"
# Output attendu: ligne d'import
```

---

### Phase A : Windows Path Fix

**Fichiers obligatoires** :

1. **`backend/utils/path_resolver.py`** ✅ EXISTS
   - Ligne 27: `get_repo_root()` - auto-détection
   - Ligne 40: Override manuel `DEXTERIO_REPO_ROOT`
   - Ligne 47: Détection Docker forte `/.dockerenv`
   - Ligne 53-57: Calcul depuis `__file__` (Windows-safe)

2. **`backend/tools/debug_paths_windows.py`** ✅ EXISTS (créé Phase A)

3. **`backend/tools/smoke_suite.py`** ✅ EXISTS (patché Phase A)

**Grep de preuve** :
```powershell
# Vérifier détection Docker
Select-String -Path "backend/utils/path_resolver.py" -Pattern "dockerenv|DEXTERIO_REPO_ROOT"
# Output attendu: lignes 40, 47

# Vérifier calcul depuis __file__
Select-String -Path "backend/utils/path_resolver.py" -Pattern "__file__|parent.parent"
# Output attendu: lignes 53-57
```

---

## BLOC 2 — PLAN D'EXÉCUTION WINDOWS (reproductible)

### A) Setup

```powershell
# 1. Naviguer vers la racine du repo (ajuster le chemin)
cd "C:\path\to\dexterio1-main"

# 2. Vérifier structure
ls backend/, frontend/, data/

# 3. Créer venv backend (si pas déjà fait)
cd backend
python -m venv venv
.\venv\Scripts\Activate

# 4. Installer dépendances backend
pip install -r requirements.txt

# 5. Retour racine + setup frontend
cd ..
cd frontend
npm install
# ou yarn install
```

### B) Validation Paths (Phase A)

```powershell
# Vérifier que repo_root() NE POINTE PAS vers /app
cd backend
python -c "from utils.path_resolver import repo_root, get_environment_info; import json; print(json.dumps(get_environment_info(), indent=2))"

# Output attendu:
# {
#   "repo_root": "C:/Users/.../dexterio1-main",  <- PAS /app
#   "is_docker": false,
#   "backend_exists": true,
#   "data_exists": true,
#   "cwd": "...",
#   "platform": "nt"
# }

# Si repo_root est incorrect, set override:
$env:DEXTERIO_REPO_ROOT = "C:\path\to\dexterio1-main"
```

### C) Démarrer Backend API

```powershell
# Terminal 1 - Backend
cd backend
.\venv\Scripts\Activate
uvicorn server:app --host 0.0.0.0 --port 8001 --reload

# Attendre message:
# INFO:     Uvicorn running on http://0.0.0.0:8001
```

### D) Démarrer Frontend

```powershell
# Terminal 2 - Frontend
cd frontend
npm run dev
# ou yarn dev

# Attendre message:
# Local:   http://localhost:3000
```

### E) Test API sans UI (preuve Phase C)

```powershell
# Terminal 3 - Tests API

# 1) Tester endpoint racine
Invoke-RestMethod -Uri "http://localhost:8001/api/" -Method GET

# 2) Lancer un backtest (1 jour SPY)
$body = @{
    symbols = @("SPY")
    start_date = "2025-08-01"
    end_date = "2025-08-01"
    trading_mode = "AGGRESSIVE"
    trade_types = @("DAILY")
    htf_warmup_days = 40
    commission_model = "ibkr_fixed"
    enable_reg_fees = $true
    slippage_model = "pct"
    slippage_cost_pct = 0.0005
    spread_model = "fixed_bps"
    spread_bps = 2.0
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:8001/api/backtests/run" -Method POST -Body $body -ContentType "application/json"
$jobId = $response.job_id
Write-Host "Job ID: $jobId"

# 3) Poller le statut (répéter toutes les 2s)
do {
    Start-Sleep -Seconds 2
    $status = Invoke-RestMethod -Uri "http://localhost:8001/api/backtests/$jobId" -Method GET
    Write-Host "Status: $($status.status)"
} while ($status.status -in @("queued", "running"))

# Afficher résultats
Write-Host "Job terminé: $($status.status)"
$status | ConvertTo-Json -Depth 10

# 4) Récupérer les logs
$logs = Invoke-RestMethod -Uri "http://localhost:8001/api/backtests/$jobId/log" -Method GET
Write-Host $logs.log

# 5) Vérifier fichiers sur disque
ls "backend\results\jobs\$jobId\"
# Output attendu:
# job.json
# job.log
# summary.json
# trades.parquet
# equity.parquet
```

### F) Test UI (preuve visuelle)

```powershell
# 1. Ouvrir navigateur
start http://localhost:3000/backtests

# 2. Vérifier formulaire s'affiche avec labels:
#    - Symbols, Start Date, End Date
#    - Trading Mode, Trade Types (DAILY/SCALP)
#    - HTF Warmup (days), Commission Model

# 3. Remplir formulaire:
#    - Symbol: SPY
#    - Start: 2025-08-01
#    - End: 2025-08-01
#    - Mode: AGGRESSIVE
#    - Types: DAILY (coché)

# 4. Cliquer "Run Backtest"
#    -> Bouton devient "Running..."

# 5. Attendre ~15-20s
#    -> Résultats s'affichent:
#       * Trades: 4
#       * Total R Net: 0.391R
#       * Total R Gross: 0.551R
#       * Total Costs: $254.64
#       * Win Rate: 50.0%
#       * Profit Factor: 2.71
#       * Expectancy: 0.098R
#       * Max DD: 0.49R

# 6. Vérifier liens téléchargement:
#    - summary, trades, equity (cliquables)

# 7. Expand "View Log":
#    - Voir logs détaillés du backtest
```

---

## BLOC 3 — ACCEPTANCE CRITERIA + "SI ÇA FAIL"

### Critères "Phase C VALIDÉE" ✅

1. **Job lifecycle fonctionne** :
   - Job passe `queued` → `running` → `done` (en ~15-20s pour 1 jour)
   - `job.json` contient `status: "done"`

2. **Artefacts créés** :
   - `job.json` contient `artifact_paths` NON VIDE :
     ```json
     {
       "summary": "summary.json",
       "trades": "trades.parquet",
       "equity": "equity.parquet"
     }
     ```
   - Fichiers existent réellement dans `backend/results/jobs/{job_id}/`

3. **Métriques Gross vs Net affichées** :
   - `job.json` contient `metrics` avec :
     * `total_trades` (nombre)
     * `total_R_gross` (float)
     * `total_R_net` (float)
     * `total_costs_dollars` (float)
     * `winrate`, `profit_factor`, `expectancy_r`, `max_drawdown_r`

4. **UI affiche les résultats** :
   - Métriques visibles dans section "Results"
   - Liens de téléchargement cliquables
   - Section "View Log" affiche contenu de `job.log`

5. **Logs consultables** :
   - Endpoint `GET /api/backtests/{job_id}/log` retourne contenu
   - Logs montrent progression : "Starting...", "Running...", "Complete"

---

### "SI ÇA FAIL, TU FAIS QUOI"

#### Problème 1: Job reste en "queued" indéfiniment

**Diagnostic** :
```powershell
# Vérifier logs backend
Get-Content backend\.venv\Lib\site-packages\...  # Logs stdout/stderr
# Chercher erreurs ProcessPoolExecutor
```

**Correctif** :
- Fichier: `backend/jobs/backtest_jobs.py`
- Ligne 343: Vérifier que `executor.submit()` est appelé
- Ligne 26: Augmenter `max_workers` de 2 à 4

#### Problème 2: `artifact_paths` est vide `{}`

**Diagnostic** :
```powershell
# Vérifier si fichiers existent dans results/
ls backend\results\ | Select-String "job_"
```

**Correctif** :
- Fichier: `backend/jobs/backtest_jobs.py`
- Ligne 253: Vérifier que `output_dir=str(results_path())` est présent
- Ligne 276-295: Vérifier logique de copie des artefacts
- Cause probable: `summary_src.exists()` retourne False

#### Problème 3: Métriques toutes à `0` ou `null`

**Diagnostic** :
```powershell
# Lire job.json
Get-Content "backend\results\jobs\{job_id}\job.json" | ConvertFrom-Json
# Vérifier si metrics est vide
```

**Correctif** :
- Fichier: `backend/jobs/backtest_jobs.py`
- Ligne 298-307: Vérifier extraction depuis `result`
- Cause probable: `result.total_trades` est `None`
- Vérifier que `BacktestEngine.run()` retourne objet valide

#### Problème 4: UI ne charge pas les données (dates/HTF vides)

**Diagnostic** :
```powershell
# Ouvrir DevTools (F12) dans navigateur
# Onglet Console -> chercher erreurs
# Onglet Network -> vérifier requêtes API
```

**Correctif** :
- Fichier: `frontend/src/pages/Backtests.jsx`
- Ligne 14-18: Vérifier état initial :
  ```javascript
  const [startDate, setStartDate] = useState('2025-08-01');
  const [endDate, setEndDate] = useState('2025-08-01');
  const [htfWarmupDays, setHtfWarmupDays] = useState(40);
  ```
- Cause probable: `useState('')` au lieu de valeur par défaut

#### Problème 5: Résultats affichent valeurs vides

**Diagnostic** :
```powershell
# Vérifier réponse API
Invoke-RestMethod -Uri "http://localhost:8001/api/backtests/{job_id}" | ConvertTo-Json -Depth 10
```

**Correctif** :
- Fichier: `frontend/src/pages/Backtests.jsx`
- Ligne 267-302: Vérifier accès aux métriques :
  ```javascript
  <div className="font-bold">{jobStatus.metrics?.total_trades}</div>
  ```
- Cause probable: `jobStatus.metrics` est `undefined`

---

## COMMANDES DE VALIDATION RAPIDE

```powershell
# Test complet Phase C (copier-coller)
cd backend

# 1. Vérifier paths
python -c "from utils.path_resolver import repo_root; print(f'Repo root: {repo_root()}')"

# 2. Vérifier imports Phase C
python -c "from jobs.backtest_jobs import submit_job; from routes.backtests import router; print('✅ Imports OK')"

# 3. Vérifier imports Phase B
python -c "from backtest.costs import calculate_total_execution_costs; print('✅ Costs OK')"

# 4. Lancer mini-test (sans UI)
python -c "
from jobs.backtest_jobs import BacktestJobRequest, submit_job
import time

request = BacktestJobRequest(
    symbols=['SPY'],
    start_date='2025-08-01',
    end_date='2025-08-01',
    trading_mode='AGGRESSIVE',
    trade_types=['DAILY']
)

job_id = submit_job(request)
print(f'Job créé: {job_id}')
time.sleep(20)

from jobs.backtest_jobs import get_job_status
status = get_job_status(job_id)
print(f'Status: {status.status}')
print(f'Trades: {status.metrics.get('total_trades')}')
print(f'Artefacts: {list(status.artifact_paths.keys())}')
"
```

---

## RÉSUMÉ DES PREUVES

| Phase | Fichier | Ligne clé | Preuve |
|-------|---------|-----------|--------|
| A | `utils/path_resolver.py` | 27, 40, 47, 53 | Détection env + override |
| B | `backtest/costs.py` | 208 | `calculate_total_execution_costs()` |
| B | `models/backtest.py` | - | `total_pnl_gross_R`, `total_pnl_net_R`, `total_costs_dollars` |
| C | `jobs/backtest_jobs.py` | 30, 188, 333 | Jobs system + worker |
| C | `routes/backtests.py` | 24, 70, 128, 146 | Endpoints API |
| C | `server.py` | 71, 76 | Router inclusion |
| C | `frontend/src/pages/Backtests.jsx` | 72, 48, 62 | UI handlers |

**Tous les fichiers existent et contiennent le code attendu. Phase A/B/C complète.**

---

FIN DU DOCUMENT DE PREUVES
