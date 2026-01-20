param(
  [Parameter(Mandatory=$true)]
  [string]$JobId
)

$ErrorActionPreference = "Stop"

$path = Join-Path -Path (Get-Location) -ChildPath ("backend\results\jobs\" + $JobId + "\debug_counts.json")
if (!(Test-Path $path)) {
  Write-Host "NOT FOUND: $path" -ForegroundColor Red
  exit 1
}

$data = Get-Content $path -Raw | ConvertFrom-Json
$c = $data.counts

Write-Host "=== FORMAT COMPACT (COPIER/COLLER) ===" -ForegroundColor Cyan
Write-Host ("candles_loaded_1m=" + $c.candles_loaded_1m)
Write-Host ("bars_processed=" + $c.bars_processed)
Write-Host ("playbooks_registered_count=" + $c.playbooks_registered_count)
Write-Host ("matches_total=" + $c.matches_total)
Write-Host ("setups_created_total=" + $c.setups_created_total)
Write-Host ("setups_after_risk_filter_total=" + $c.setups_after_risk_filter_total)
Write-Host ("trades_open_attempted_total=" + $c.trades_open_attempted_total)
Write-Host ("trades_opened_total=" + $c.trades_opened_total)
Write-Host ("missing_playbook_name=" + $c.missing_playbook_name)
Write-Host ("rejected_by_mode_total=" + $c.rejected_by_mode_total)

Write-Host "`n=== setups_created_by_playbook ===" -ForegroundColor Cyan
($c.setups_created_by_playbook | ConvertTo-Json -Depth 10)

Write-Host "`n=== risk_mode_used ===" -ForegroundColor Cyan
$c.risk_mode_used

Write-Host "`n=== risk_allowlist_snapshot ===" -ForegroundColor Cyan
($c.risk_allowlist_snapshot | ConvertTo-Json -Depth 10)

Write-Host "`n=== risk_rejects_by_playbook ===" -ForegroundColor Cyan
($c.risk_rejects_by_playbook | ConvertTo-Json -Depth 10)

Write-Host "`n=== risk_reject_examples ===" -ForegroundColor Cyan
($c.risk_reject_examples | ConvertTo-Json -Depth 10)

Write-Host "`n=== trades_open_rejected_by_reason ===" -ForegroundColor Cyan
($c.trades_open_rejected_by_reason | ConvertTo-Json -Depth 10)
