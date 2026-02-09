$ErrorActionPreference = 'Stop'
$ROOT = (Split-Path -Parent (Split-Path -Parent $PSCommandPath))
$STAMP = (Get-Date -Format 'yyyyMMdd-HHmmss')
$Snap = Join-Path $env:TEMP "contracts_llm_snapshot_$STAMP"
$Zip  = Join-Path $ROOT "backups\contracts_llm_$STAMP.zip"
New-Item -ItemType Directory -Force -Path $Snap | Out-Null

Write-Host "
[backup] Snapshot -> ZIP ..." -ForegroundColor Cyan
$xd = @(
  "/XD", (Join-Path $ROOT ".venv"),
  "/XD", (Join-Path $ROOT "backups"),
  "/XD", (Join-Path $ROOT "data\index\.cache")
)
robocopy $ROOT $Snap /MIR /R:1 /W:1 /SL /NFL /NDL /NP @xd | Out-Null
if (Test-Path $Zip) { Remove-Item $Zip -Force }
Compress-Archive -Path (Join-Path $Snap '*') -DestinationPath $Zip -Force
Remove-Item $Snap -Recurse -Force -EA SilentlyContinue

Write-Host "[backup] DONE -> $Zip" -ForegroundColor Green
