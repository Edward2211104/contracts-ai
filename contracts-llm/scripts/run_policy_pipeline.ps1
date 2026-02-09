Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# --- Rutas base ---
$projRoot     = "C:\Users\Usuario\contracts-ai\contracts-llm"
$downloadDir  = "C:\Users\Usuario\Downloads\public-policies"
$rawDir       = Join-Path $projRoot "data\policies_raw"
$processedDir = Join-Path $projRoot "data\policies_processed"

Set-Location $projRoot

Write-Host "[INFO] Proyecto:  $projRoot"      -ForegroundColor Cyan
Write-Host "[INFO] Descargas: $downloadDir"   -ForegroundColor Cyan
Write-Host "[INFO] RAW PDFs:  $rawDir"        -ForegroundColor Cyan
Write-Host "[INFO] JSON proc: $processedDir`n" -ForegroundColor Cyan

# --- Crear carpetas necesarias ---
foreach ($dir in @($downloadDir, $rawDir, $processedDir)) {
    if (-not (Test-Path $dir)) {
        Write-Host "[INFO] Creando carpeta: $dir" -ForegroundColor Yellow
        New-Item -ItemType Directory -Path $dir | Out-Null
    }
}

# --- Leer URLs desde policy_urls.txt ---
$urlsFile = Join-Path $projRoot "policy_urls.txt"
$urls = @()

if (Test-Path $urlsFile) {
    Write-Host "[INFO] Leyendo URLs desde policy_urls.txt..." -ForegroundColor Cyan
    $urls = Get-Content $urlsFile | Where-Object { $_.Trim() -ne "" -and -not $_.Trim().StartsWith("#") }
} else {
    Write-Host "[WARN] No existe policy_urls.txt; crea ese archivo con una URL de PDF por línea." -ForegroundColor Yellow
}

# --- Descargar PDFs ---
Write-Host "`n[STEP] Descargando pólizas públicas..." -ForegroundColor Cyan

foreach ($u in $urls) {
    $trimmed = $u.Trim()
    if ($trimmed -eq "") { continue }

    $fileName = [System.IO.Path]::GetFileName($trimmed)
    if (-not $fileName.ToLower().EndsWith(".pdf")) {
        $fileName = $fileName + ".pdf"
    }

    $destPath = Join-Path $downloadDir $fileName

    if (Test-Path $destPath) {
        Write-Host " - Ya existe: $fileName (omitido)" -ForegroundColor DarkGray
        continue
    }

    try {
        Write-Host " - Descargando: $fileName" -ForegroundColor Green
        Invoke-WebRequest -Uri $trimmed -OutFile $destPath -UseBasicParsing
    }
    catch {
        Write-Host "   [ERR] Falló descarga de $trimmed : $($_.Exception.Message)" -ForegroundColor Red
    }
}

# --- Copiar a data\policies_raw ---
Write-Host "`n[STEP] Copiando PDFs a $rawDir..." -ForegroundColor Cyan

$downloadedPdfs = Get-ChildItem $downloadDir -Filter *.pdf -File -ErrorAction SilentlyContinue

if (-not $downloadedPdfs) {
    Write-Host "[ERR] No hay PDFs en $downloadDir. Sin PDFs no hay índice vectorial." -ForegroundColor Red
    return
}

foreach ($pdf in $downloadedPdfs) {
    $dest = Join-Path $rawDir $pdf.Name
    Copy-Item -Path $pdf.FullName -Destination $dest -Force
}

Write-Host "[OK] Copiados $($downloadedPdfs.Count) PDFs a $rawDir." -ForegroundColor Green

# --- Ejecutar ingest_policies.py ---
Write-Host "`n[STEP] Ejecutando ingest_policies.py..." -ForegroundColor Cyan
try {
    .\.venv\Scripts\python.exe ingest_policies.py
}
catch {
    Write-Host "[ERR] Error al ejecutar ingest_policies.py: $($_.Exception.Message)" -ForegroundColor Red
    return
}

$processedJson = Get-ChildItem $processedDir -Filter *.json -File -ErrorAction SilentlyContinue
if (-not $processedJson) {
    Write-Host "[ERR] ingest_policies.py terminó sin JSON en $processedDir." -ForegroundColor Red
    return
}
Write-Host "[OK] JSON de pólizas procesadas: $($processedJson.Count) archivos." -ForegroundColor Green

# --- Ejecutar build_vector_index.py ---
Write-Host "`n[STEP] Ejecutando build_vector_index.py..." -ForegroundColor Cyan
try {
    .\.venv\Scripts\python.exe build_vector_index.py
}
catch {
    Write-Host "[ERR] Error al ejecutar build_vector_index.py: $($_.Exception.Message)" -ForegroundColor Red
    return
}

Write-Host "`n[OK] Pipeline COMPLETO: descargas + ingestión + índice vectorial." -ForegroundColor Green
