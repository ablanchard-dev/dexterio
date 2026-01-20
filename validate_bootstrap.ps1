# 🔥 BLOC 0 — Script de Validation Bootstrap
# Usage: .\validate_bootstrap.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "BLOC 0 — VALIDATION BOOTSTRAP" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ÉTAPE 0.1 — Positionnement
Write-Host "[0.1] Vérification positionnement..." -ForegroundColor Yellow
$currentDir = Get-Location
if ($currentDir.Path -ne "C:\bots\dexterio1-main") {
    Write-Host "  ⚠️  Vous n'êtes pas dans C:\bots\dexterio1-main" -ForegroundColor Red
    Write-Host "  Exécutez: cd C:\bots\dexterio1-main" -ForegroundColor Yellow
    exit 1
}
Write-Host "  ✅ Positionnement OK: $($currentDir.Path)" -ForegroundColor Green
Write-Host ""

# ÉTAPE 0.2 — Python
Write-Host "[0.2] Vérification Python..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ❌ Python non trouvé" -ForegroundColor Red
    exit 1
}
Write-Host "  ✅ $pythonVersion" -ForegroundColor Green
Write-Host ""

# ÉTAPE 0.3 — Venv
Write-Host "[0.3] Vérification venv..." -ForegroundColor Yellow
if (-not (Test-Path ".\venv\Scripts\Activate.ps1")) {
    Write-Host "  ❌ venv non trouvé" -ForegroundColor Red
    Write-Host "  Création du venv..." -ForegroundColor Yellow
    python -m venv venv
}
Write-Host "  ✅ venv trouvé" -ForegroundColor Green
Write-Host ""

# ÉTAPE 0.4 — Dépendances
Write-Host "[0.4] Vérification dépendances..." -ForegroundColor Yellow
& .\venv\Scripts\python.exe -c "import fastapi, uvicorn, pandas, pydantic; print('OK')" 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ⚠️  Dépendances manquantes" -ForegroundColor Yellow
    Write-Host "  Installation des dépendances..." -ForegroundColor Yellow
    & .\venv\Scripts\pip.exe install -q -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ❌ Échec installation" -ForegroundColor Red
        exit 1
    }
}
Write-Host "  ✅ Dépendances OK" -ForegroundColor Green
Write-Host ""

# ÉTAPE 0.5 — Données
Write-Host "[0.5] Vérification données historiques..." -ForegroundColor Yellow
$spyPath = & .\venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'backend'); from utils.path_resolver import historical_data_path; spy = historical_data_path('1m', 'SPY.parquet'); print(str(spy))" 2>&1
if ($LASTEXITCODE -eq 0) {
    if (Test-Path $spyPath) {
        Write-Host "  ✅ SPY.parquet trouvé: $spyPath" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  SPY.parquet non trouvé: $spyPath" -ForegroundColor Yellow
        Write-Host "     Le backtest échouera, mais l'UI fonctionnera" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ⚠️  Erreur lors de la vérification des données" -ForegroundColor Yellow
}
Write-Host ""

# ÉTAPE 0.6 — Backend
Write-Host "[0.6] Vérification backend..." -ForegroundColor Yellow
if (Test-Path ".\backend\server.py") {
    Write-Host "  ✅ backend/server.py trouvé" -ForegroundColor Green
} else {
    Write-Host "  ❌ backend/server.py non trouvé" -ForegroundColor Red
    exit 1
}
Write-Host ""

# ÉTAPE 0.7 — Frontend
Write-Host "[0.7] Vérification frontend..." -ForegroundColor Yellow
if (Test-Path ".\frontend\package.json") {
    Write-Host "  ✅ frontend/package.json trouvé" -ForegroundColor Green
} else {
    Write-Host "  ❌ frontend/package.json non trouvé" -ForegroundColor Red
    exit 1
}
Write-Host ""

# RÉSUMÉ
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "✅ VALIDATION TERMINÉE" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "PROCHAINES ÉTAPES MANUELLES:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Terminal 1 — Backend:" -ForegroundColor Cyan
Write-Host "   cd C:\bots\dexterio1-main" -ForegroundColor White
Write-Host "   .\.venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "   cd backend" -ForegroundColor White
Write-Host "   uvicorn server:app --host 0.0.0.0 --port 8001 --reload" -ForegroundColor White
Write-Host ""
Write-Host "2. Terminal 2 — Frontend:" -ForegroundColor Cyan
Write-Host "   cd C:\bots\dexterio1-main\frontend" -ForegroundColor White
Write-Host "   yarn install" -ForegroundColor White
Write-Host "   yarn start" -ForegroundColor White
Write-Host ""
Write-Host "3. Navigateur:" -ForegroundColor Cyan
Write-Host "   http://localhost:3000/backtests" -ForegroundColor White
Write-Host ""


