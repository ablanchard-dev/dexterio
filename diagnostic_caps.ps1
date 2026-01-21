param(
    [Parameter(Mandatory = $true)]
    [string]$JobId
)

Push-Location (Split-Path -Parent $MyInvocation.MyCommand.Path)

try {
    $debugFile = Get-ChildItem "backend\results\jobs\$JobId\debug_counts*.json" -ErrorAction Stop | Select-Object -First 1
} catch {
    Write-Host "❌ Impossible de trouver debug_counts pour JobId=$JobId" -ForegroundColor Red
    Pop-Location
    exit 1
}

$data = Get-Content $debugFile.FullName -Raw | ConvertFrom-Json
$c = $data.counts

Write-Host "`n=== DIAGNOSTIC CAPS / LIMITES ===" -ForegroundColor Cyan

Write-Host "trades_opened_total           : $($c.trades_opened_total)" -ForegroundColor Green
Write-Host "trades_open_attempted_total   : $($c.trades_open_attempted_total)" -ForegroundColor Green

Write-Host "`n--- REJETS OUVERTURE (par raison) ---" -ForegroundColor Yellow
$rej = $c.trades_open_rejected_by_reason
if ($rej) {
    $rej.GetEnumerator() | Sort-Object -Property Value -Descending | ForEach-Object {
        Write-Host ("{0,-30} {1,5}" -f $_.Key, $_.Value)
    }
} else {
    Write-Host "(aucun rejet instrumenté)" -ForegroundColor DarkGray
}

Write-Host "`n--- CAPS SNAPSHOT ---" -ForegroundColor Yellow
$caps = $c.caps_snapshot
if ($caps) {
    Write-Host ("AGGRESSIVE: daily_cap={0}, per_playbook_session_cap={1}, hard_daily_cap={2}, n_active_playbooks={3}" -f `
        $caps.aggressive.daily_cap, `
        $caps.aggressive.per_playbook_session_cap, `
        $caps.aggressive.hard_daily_cap, `
        $caps.aggressive.n_active_playbooks)
    Write-Host ("SAFE      : daily_cap={0}, per_playbook_session_cap={1}" -f `
        $caps.safe.daily_cap, `
        $caps.safe.per_playbook_session_cap)
} else {
    Write-Host "(aucun caps_snapshot trouvé)" -ForegroundColor DarkGray
}

Write-Host "`nsession_key_used             : $($c.session_key_used)" -ForegroundColor Yellow

Write-Host "`n--- TRADES PAR PLAYBOOK (ouverts) ---" -ForegroundColor Yellow
$opened = $c.trades_opened_by_playbook
if ($opened) {
    $opened.GetEnumerator() | Sort-Object -Property Value -Descending | Select-Object -First 10 | ForEach-Object {
        Write-Host ("{0,-40} {1,5}" -f $_.Key, $_.Value)
    }
} else {
    Write-Host "(aucun trade ouvert par playbook)" -ForegroundColor DarkGray
}

Write-Host "`n--- LIMITES SESSION (session_limit_reached_by_playbook) ---" -ForegroundColor Yellow
$sess = $c.session_limit_reached_by_playbook
if ($sess) {
    $sess.GetEnumerator() | Sort-Object -Property Value -Descending | Select-Object -First 10 | ForEach-Object {
        Write-Host ("{0,-40} {1,5}" -f $_.Key, $_.Value)
    }
} else {
    Write-Host "(aucune session_limit_reached instrumentée)" -ForegroundColor DarkGray
}

Pop-Location


