# ==========================================
# RUN-STABLE.ps1  (Stable local run)
# - Starts ONLY the real app folders (contracts-llm + contracts-ui)
# - Kills stale processes on ports
# - Runs health checks (OPTIONS + POST + UI)
# ==========================================
$ErrorActionPreference="Stop"

$ROOT = "C:\Users\Usuario\contracts-ai"
$LLM_DIR = Join-Path $ROOT "contracts-llm"
$UI_DIR  = Join-Path $ROOT "contracts-ui"

if (-not (Test-Path $LLM_DIR)) { throw "Missing: $LLM_DIR" }
if (-not (Test-Path $UI_DIR))  { throw "Missing: $UI_DIR" }

function Kill-Port($port) {
  $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
  foreach ($c in $conns) {
    try {
      $p = Get-Process -Id $c.OwningProcess -ErrorAction SilentlyContinue
      if ($p) {
        Write-Host "Stopping PID $($p.Id) ($($p.ProcessName)) on port $port" -ForegroundColor Yellow
        Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
      }
    } catch {}
  }
}

function Wait-Http($url, $seconds=25) {
  $start = Get-Date
  while (((Get-Date) - $start).TotalSeconds -lt $seconds) {
    try {
      $r = Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 3
      if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500) { return $true }
    } catch {}
    Start-Sleep -Milliseconds 500
  }
  return $false
}

Write-Host "== Clean ports ==" -ForegroundColor Cyan
Kill-Port 4050
Kill-Port 3020

Write-Host "`n== Start backend ==" -ForegroundColor Cyan
$backendScript = Join-Path $ROOT "contracts-llm\start-backend.ps1"
if (-not (Test-Path $backendScript)) { throw "Missing: $backendScript" }

Start-Process powershell -ArgumentList "-NoExit","-ExecutionPolicy","Bypass","-File","`"$backendScript`""

Write-Host "Waiting backend http://127.0.0.1:4050 ..." -ForegroundColor Cyan
if (-not (Wait-Http "http://127.0.0.1:4050/docs" 25)) {
  Write-Host "Backend did not become reachable at /docs. Check backend window logs." -ForegroundColor Red
} else {
  Write-Host "Backend reachable." -ForegroundColor Green
}

Write-Host "`n== Start UI ==" -ForegroundColor Cyan
$uiScript = Join-Path $ROOT "contracts-ui\start-ui.ps1"
if (-not (Test-Path $uiScript)) { throw "Missing: $uiScript" }

Start-Process powershell -ArgumentList "-NoExit","-ExecutionPolicy","Bypass","-File","`"$uiScript`""

Write-Host "Waiting UI http://localhost:3020 ..." -ForegroundColor Cyan
if (-not (Wait-Http "http://localhost:3020" 25)) {
  Write-Host "UI did not become reachable. Check UI window logs." -ForegroundColor Red
} else {
  Write-Host "UI reachable." -ForegroundColor Green
}

Write-Host "`n== Health checks (CORS preflight + POST) ==" -ForegroundColor Cyan
$uri = "http://127.0.0.1:4050/llm/ask-basic"

try {
  $opt = Invoke-WebRequest -UseBasicParsing -Method OPTIONS -Uri $uri -Headers @{
    Origin="http://localhost:3020"
    "Access-Control-Request-Method"="POST"
    "Access-Control-Request-Headers"="content-type"
  } -TimeoutSec 8
  Write-Host "OPTIONS: $($opt.StatusCode)  Allow-Origin: $($opt.Headers["Access-Control-Allow-Origin"])" -ForegroundColor Green
} catch {
  Write-Host "OPTIONS FAILED (this breaks the browser). Error: $($_.Exception.Message)" -ForegroundColor Red
}

try {
  $body = @{ question="ping"; contractText="test" } | ConvertTo-Json
  $post = Invoke-WebRequest -UseBasicParsing -Method POST -Uri $uri -ContentType "application/json" -Body $body -Headers @{
    Origin="http://localhost:3020"
  } -TimeoutSec 20
  Write-Host "POST: $($post.StatusCode)  Allow-Origin: $($post.Headers["Access-Control-Allow-Origin"])" -ForegroundColor Green
} catch {
  Write-Host "POST FAILED. Error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n✅ Done. Open: http://localhost:3020" -ForegroundColor Cyan
