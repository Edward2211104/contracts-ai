$ErrorActionPreference = 'Stop'
$ROOT = (Split-Path -Parent (Split-Path -Parent $PSCommandPath))
$venv = Join-Path $ROOT '.venv\Scripts\Activate.ps1'
. $venv
python "$ROOT\eval\eval.py"
