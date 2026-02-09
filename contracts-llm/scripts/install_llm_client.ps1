Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Set-Location "C:\Users\Usuario\contracts-ai\contracts-llm"

Write-Host "[STEP] Installing Python 'openai' client (for LM Studio local server)..." -ForegroundColor Cyan
.\.venv\Scripts\pip.exe install openai --upgrade

Write-Host "`n[OK] 'openai' client installed inside the venv." -ForegroundColor Green
Write-Host "[STEP] Now start or restart the LLM backend in ANOTHER console with:" -ForegroundColor Yellow
Write-Host "    cd C:\Users\Usuario\contracts-ai\contracts-llm" -ForegroundColor Yellow
Write-Host "    .\.venv\Scripts\python.exe main.py" -ForegroundColor Yellow
