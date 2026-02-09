$ErrorActionPreference = 'Stop'

# setup_llm_env.ps1 - prepara el entorno Python del LLM (experto en contratos)

# Raíz de contracts-llm (un nivel arriba de /scripts)
$root      = Resolve-Path (Join-Path $PSScriptRoot '..')
$venvDir   = Join-Path $root '.venv'
$pythonExe = Join-Path $venvDir 'Scripts\python.exe'

if (-not (Test-Path $pythonExe)) {
    Write-Host '[SETUP] Creating virtual environment (.venv)...' -ForegroundColor Cyan
    python -m venv $venvDir
    $pythonExe = Join-Path $venvDir 'Scripts\python.exe'
}

Write-Host "[SETUP] Using Python: $pythonExe"

# Actualizar pip
& $pythonExe -m pip install --upgrade pip

# Instalar requirements del LLM
$reqFile = Join-Path $root 'requirements.txt'
if (Test-Path $reqFile) {
    Write-Host '[SETUP] Installing packages from requirements.txt...' -ForegroundColor Cyan
    & $pythonExe -m pip install -r $reqFile
} else {
    Write-Host '[WARN] requirements.txt not found, installing core deps (fastapi, uvicorn, httpx, pydantic, python-dotenv)...' -ForegroundColor Yellow
    & $pythonExe -m pip install fastapi "uvicorn[standard]" httpx pydantic python-dotenv
}

Write-Host '[OK] LLM Python environment ready.' -ForegroundColor Green
