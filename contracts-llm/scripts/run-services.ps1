$ErrorActionPreference = 'Stop'
$ROOT = (Split-Path -Parent (Split-Path -Parent $PSCommandPath))
$venv = Join-Path $ROOT '.venv\Scripts\Activate.ps1'
. $venv

# Make sure Ollama and model
if (-not (Get-Command 'ollama' -EA SilentlyContinue)) {
  Write-Warning "Ollama is not installed. Install and start it if you want local LLM answers."
} else {
  try { ollama serve | Out-Null } catch {}
  try { ollama pull llama3.1:latest | Out-Null } catch {}
}

Start-Process powershell -ArgumentList "label-studio start" -WindowStyle Minimized | Out-Null
Start-Sleep -Seconds 2

# Start RAG API
Write-Host "
Starting RAG API at http://127.0.0.1:8000 ..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "uvicorn src.answerer.rag_api:app --reload --port 8000" -WindowStyle Normal | Out-Null
Write-Host "Open: http://127.0.0.1:8000/docs" -ForegroundColor Yellow
