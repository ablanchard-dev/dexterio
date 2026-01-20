# Test P0 Fix - Validation Unicode + Job Status
# Usage: .\test_p0_fix.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "TEST P0 FIX - Validation" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Vérifier que le backend tourne
Write-Host "[1] Vérification backend..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/" -Method GET -ErrorAction Stop
    Write-Host "  ✅ Backend accessible" -ForegroundColor Green
} catch {
    Write-Host "  ❌ Backend non accessible. Lancez: uvicorn server:app --host 0.0.0.0 --port 8001 --reload" -ForegroundColor Red
    exit 1
}
Write-Host ""

# 2. Reset stale jobs
Write-Host "[2] Reset des jobs stale..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/backtests/reset_stale" -Method POST -ErrorAction Stop
    Write-Host "  ✅ Jobs reset: $($response.reset_count)" -ForegroundColor Green
} catch {
    Write-Host "  ⚠️  Erreur reset (normal si pas de jobs stale)" -ForegroundColor Yellow
}
Write-Host ""

# 3. Lancer un backtest test
Write-Host "[3] Lancement backtest test..." -ForegroundColor Yellow
$testRequest = @{
    symbols = @("SPY")
    start_date = "2025-08-01"
    end_date = "2025-08-01"
    trading_mode = "SAFE"
    trade_types = @("DAILY")
    htf_warmup_days = 40
    initial_capital = 50000.0
    commission_model = "ibkr_fixed"
    enable_reg_fees = $true
    slippage_model = "pct"
    slippage_cost_pct = 0.0005
    spread_model = "fixed_bps"
    spread_bps = 2.0
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/backtests/run" -Method POST -Body $testRequest -ContentType "application/json" -ErrorAction Stop
    $jobId = $response.job_id
    Write-Host "  ✅ Job créé: $jobId" -ForegroundColor Green
} catch {
    Write-Host "  ❌ Erreur création job: $_" -ForegroundColor Red
    exit 1
}
Write-Host ""

# 4. Poll status
Write-Host "[4] Polling status (max 60s)..." -ForegroundColor Yellow
$maxWait = 60
$elapsed = 0
$status = "queued"

while ($elapsed -lt $maxWait) {
    Start-Sleep -Seconds 2
    $elapsed += 2
    
    try {
        $statusData = Invoke-RestMethod -Uri "http://localhost:8001/api/backtests/$jobId" -Method GET -ErrorAction Stop
        $status = $statusData.status
        Write-Host "  [$elapsed s] Status: $status" -ForegroundColor Cyan
        
        if ($status -eq "done") {
            Write-Host "  ✅ Job terminé avec succès!" -ForegroundColor Green
            Write-Host "  Métriques:" -ForegroundColor Yellow
            $statusData.metrics.PSObject.Properties | ForEach-Object {
                Write-Host "    $($_.Name): $($_.Value)" -ForegroundColor White
            }
            break
        } elseif ($status -eq "failed") {
            Write-Host "  ❌ Job échoué: $($statusData.error)" -ForegroundColor Red
            break
        }
    } catch {
        Write-Host "  ⚠️  Erreur polling: $_" -ForegroundColor Yellow
    }
}

if ($status -notin @("done", "failed")) {
    Write-Host "  ⏱️  Timeout après $maxWait s" -ForegroundColor Yellow
}
Write-Host ""

# 5. Vérifier les fichiers
Write-Host "[5] Vérification fichiers..." -ForegroundColor Yellow
.\.venv\Scripts\Activate.ps1
$filesCheck = python -c "import sys; sys.path.insert(0, 'backend'); from utils.path_resolver import results_path; from pathlib import Path; job_dir = results_path('jobs', '$jobId'); print('Job dir:', job_dir); print('Exists:', job_dir.exists()); files = [f.name for f in job_dir.iterdir() if f.is_file()]; print('Files:', ', '.join(files))"
Write-Host $filesCheck
Write-Host ""

# 6. Vérifier le log (pas d'erreur Unicode)
Write-Host "[6] Vérification log (encodage UTF-8)..." -ForegroundColor Yellow
try {
    $logData = Invoke-RestMethod -Uri "http://localhost:8001/api/backtests/$jobId/log" -Method GET -ErrorAction Stop
    if ($logData.log -match "UnicodeEncodeError") {
        Write-Host "  ❌ Erreur Unicode détectée dans le log!" -ForegroundColor Red
    } else {
        Write-Host "  ✅ Pas d'erreur Unicode dans le log" -ForegroundColor Green
        Write-Host "  Dernières lignes:" -ForegroundColor Cyan
        $logData.log -split "`n" | Select-Object -Last 3 | ForEach-Object { Write-Host "    $_" -ForegroundColor White }
    }
} catch {
    Write-Host "  ⚠️  Erreur lecture log: $_" -ForegroundColor Yellow
}
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "TEST TERMINÉ" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Résultat attendu:" -ForegroundColor Yellow
Write-Host "  - Job status: done OU failed (pas running infini)" -ForegroundColor White
Write-Host "  - Pas d'erreur UnicodeEncodeError dans le log" -ForegroundColor White
Write-Host "  - Fichiers présents: job.json, job.log, summary.json (si done)" -ForegroundColor White
Write-Host ""

