# P0 DIAGNOSTIC - Script pour analyser debug_counts.json
# Usage: .\diagnostic_p0.ps1 -JobId "job_xxxxx"

param(
    [Parameter(Mandatory=$true)]
    [string]$JobId
)

$ErrorActionPreference = "Stop"

# Chercher le fichier debug_counts
$jobsDir = "backend\results\jobs\$JobId"
if (-not (Test-Path $jobsDir)) {
    Write-Host "❌ Répertoire job introuvable: $jobsDir" -ForegroundColor Red
    exit 1
}

$debugFile = Get-ChildItem "$jobsDir\debug_counts*.json" -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $debugFile) {
    Write-Host "❌ Fichier debug_counts.json introuvable dans $jobsDir" -ForegroundColor Red
    exit 1
}

# Charger les données
try {
    $data = Get-Content $debugFile.FullName -Raw | ConvertFrom-Json
} catch {
    Write-Host "❌ Erreur lors du chargement du JSON: $_" -ForegroundColor Red
    exit 1
}

# Extraire les compteurs (avec valeurs par défaut si absents)
$counts = $data.counts
if (-not $counts) {
    Write-Host "❌ Structure JSON invalide: pas de champ 'counts'" -ForegroundColor Red
    exit 1
}

# Afficher les 10 champs clés
Write-Host "`n=== P0 DIAGNOSTIC - 10 CHAMPS CLES ===" -ForegroundColor Cyan
Write-Host "Job ID: $JobId" -ForegroundColor Gray
Write-Host "Fichier: $($debugFile.Name)" -ForegroundColor Gray
Write-Host ""

# Extraction sécurisée avec valeurs par défaut
$candles_loaded_1m = if ($counts.candles_loaded_1m) { $counts.candles_loaded_1m } else { 0 }
$playbooks_registered_count = if ($counts.playbooks_registered_count) { $counts.playbooks_registered_count } else { 0 }
$matches_total = if ($counts.matches_total) { $counts.matches_total } else { 0 }
$setups_created_total = if ($counts.setups_created_total) { $counts.setups_created_total } else { 0 }
$setups_after_risk_filter_total = if ($counts.setups_after_risk_filter_total) { $counts.setups_after_risk_filter_total } else { 0 }
$trades_open_attempted_total = if ($counts.trades_open_attempted_total) { $counts.trades_open_attempted_total } else { 0 }
$trades_opened_total = if ($counts.trades_opened_total) { $counts.trades_opened_total } else { 0 }
$missing_playbook_name = if ($counts.missing_playbook_name) { $counts.missing_playbook_name } else { 0 }
$rejected_by_mode_total = if ($counts.setups_rejected_by_mode) { $counts.setups_rejected_by_mode } else { 0 }
$open_reject_reasons = if ($counts.trades_open_rejected_by_reason) { $counts.trades_open_rejected_by_reason } else { @{} }

# Format compact pour copier/coller
Write-Host "--- FORMAT COMPACT (COPIER/COLLER) ---" -ForegroundColor Yellow
"candles_loaded_1m=$candles_loaded_1m"
"playbooks_registered_count=$playbooks_registered_count"
"matches_total=$matches_total"
"setups_created_total=$setups_created_total"
"setups_after_risk_filter_total=$setups_after_risk_filter_total"
"trades_open_attempted_total=$trades_open_attempted_total"
"trades_opened_total=$trades_opened_total"
"missing_playbook_name=$missing_playbook_name"
"rejected_by_mode_total=$rejected_by_mode_total"
"open_reject_reasons=$(($open_reject_reasons | ConvertTo-Json -Compress))"

Write-Host "`n--- DETAILS (READABLE) ---" -ForegroundColor Yellow
Write-Host "1. candles_loaded_1m: $candles_loaded_1m" -ForegroundColor White
Write-Host "2. playbooks_registered_count: $playbooks_registered_count" -ForegroundColor White
Write-Host "3. matches_total: $matches_total" -ForegroundColor White
Write-Host "4. setups_created_total: $setups_created_total" -ForegroundColor White
Write-Host "5. setups_after_risk_filter_total: $setups_after_risk_filter_total" -ForegroundColor White
Write-Host "6. trades_open_attempted_total: $trades_open_attempted_total" -ForegroundColor White
Write-Host "7. trades_opened_total: $trades_opened_total" -ForegroundColor $(if ($trades_opened_total -gt 0) { "Green" } else { "Red" })
Write-Host "8. missing_playbook_name: $missing_playbook_name" -ForegroundColor $(if ($missing_playbook_name -eq 0) { "Green" } else { "Red" })
Write-Host "9. rejected_by_mode_total: $rejected_by_mode_total" -ForegroundColor White

if ($open_reject_reasons -and ($open_reject_reasons | Measure-Object).Count -gt 0) {
    Write-Host "10. open_reject_reasons:" -ForegroundColor White
    $open_reject_reasons | ConvertTo-Json | Write-Host
} else {
    Write-Host "10. open_reject_reasons: {}" -ForegroundColor Gray
}

# Diagnostic automatique
Write-Host "`n=== DIAGNOSTIC AUTOMATIQUE ===" -ForegroundColor Cyan

if ($trades_opened_total -gt 0) {
    Write-Host "✅ CAS A: trades_opened_total > 0" -ForegroundColor Green
    Write-Host "   => Pipeline OK. Prêt pour P1 (reporting playbook-by-playbook + graphs UI)." -ForegroundColor Green
    exit 0
}

if ($setups_after_risk_filter_total -eq 0) {
    Write-Host "❌ CAS B: setups_after_risk_filter_total = 0" -ForegroundColor Red
    Write-Host "   => Blocage RiskEngine (allowlist/denylist/kill-switch/mode)." -ForegroundColor Red
    
    # Afficher détails des rejets
    if ($counts.setups_rejected_by_mode_by_playbook -and ($counts.setups_rejected_by_mode_by_playbook | Measure-Object).Count -gt 0) {
        Write-Host "`n   Rejets par playbook:" -ForegroundColor Yellow
        $counts.setups_rejected_by_mode_by_playbook | ConvertTo-Json | Write-Host
    }
    
    if ($counts.setups_rejected_by_mode_examples -and $counts.setups_rejected_by_mode_examples.Count -gt 0) {
        Write-Host "`n   Exemples de rejets (max 3):" -ForegroundColor Yellow
        $counts.setups_rejected_by_mode_examples | ConvertTo-Json | Write-Host
    }
    
    Write-Host "`n   Action: Corriger le filtre allowlist/denylist/mode." -ForegroundColor Yellow
    exit 2
}

if ($setups_after_risk_filter_total -gt 0 -and $trades_opened_total -eq 0) {
    Write-Host "❌ CAS C: setups_after_risk_filter_total > 0 MAIS trades_opened_total = 0" -ForegroundColor Red
    Write-Host "   => Blocage au moment d'ouvrir (cooldown/session limit/sizing/spread/cap)." -ForegroundColor Red
    
    if ($open_reject_reasons -and ($open_reject_reasons | Measure-Object).Count -gt 0) {
        Write-Host "`n   Raisons de rejet d'ouverture:" -ForegroundColor Yellow
        $open_reject_reasons | ConvertTo-Json | Write-Host
        
        # Identifier la raison #1
        $topReason = $open_reject_reasons | Get-Member -MemberType NoteProperty | ForEach-Object {
            [PSCustomObject]@{
                Reason = $_.Name
                Count = $open_reject_reasons.($_.Name)
            }
        } | Sort-Object Count -Descending | Select-Object -First 1
        
        if ($topReason) {
            Write-Host "`n   ⚠️  Raison #1: '$($topReason.Reason)' (count=$($topReason.Count))" -ForegroundColor Yellow
        }
    } else {
        Write-Host "`n   ⚠️  Aucune raison de rejet capturée (bug instrumentation?)." -ForegroundColor Yellow
    }
    
    Write-Host "`n   Action: Corriger la raison de rejet identifiée." -ForegroundColor Yellow
    exit 3
}

# Cas inattendu
Write-Host "⚠️  CAS INATTENDU: Impossible de déterminer le diagnostic." -ForegroundColor Yellow
exit 1

