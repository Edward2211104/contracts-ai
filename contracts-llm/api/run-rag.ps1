$ErrorActionPreference='Stop'
$BASE = Join-Path (Split-Path -Parent "") '..'
$BASE = (Resolve-Path $BASE).Path
$ENV  = Join-Path $BASE '.venv'
$IDXD = Join-Path $BASE 'data\index'

if (!(Test-Path $ENV)) { python -m venv $ENV }
. (Join-Path $ENV 'Scripts\Activate.ps1')
python -m pip install --upgrade pip wheel setuptools | Out-Null
pip install -q fastapi 'uvicorn[standard]' sentence-transformers faiss-cpu pandas requests | Out-Null

$env:IDXD = $IDXD
if (-not $env:OLLAMA_URL) { $env:OLLAMA_URL = 'http://127.0.0.1:11434' }
if (-not $env:API_MODEL)   { $env:API_MODEL   = 'llama3.1:latest' }

# libera puerto 8000 y lanza
function Stop-Port([int]$Port){
  $pids = Get-NetTCPConnection -State Listen -LocalPort $Port -EA SilentlyContinue | Select -Expand OwningProcess -Unique
  foreach($p in $pids){ try{ Stop-Process -Id $p -Force -EA SilentlyContinue }catch{} }
}
Stop-Port 8000

uvicorn contracts-llm.api.rag_api:app --host 127.0.0.1 --port 8000 --workers 1
