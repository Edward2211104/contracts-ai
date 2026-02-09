param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projRoot

$venvPy = Join-Path $projRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $venvPy)) {
    Write-Host "[ERR] No se encontró $venvPy" -ForegroundColor Red
    Write-Host "      Primero ejecuta el script de entorno (setup_llm_env.ps1)." -ForegroundColor Yellow
    exit 1
}

Write-Host "[LLM] Iniciando servidor LLM en http://127.0.0.1:4050 ..." -ForegroundColor Green
Write-Host "[LLM] Usa Ctrl+C para detenerlo." -ForegroundColor Yellow

& $venvPy "main.py"
