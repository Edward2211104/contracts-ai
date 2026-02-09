param(
    [string]$DownloadDir = (Join-Path $env:USERPROFILE "Downloads\\public-policies")
)

# Detect project root (this script lives in ...\\contracts-llm\\scripts)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$rootDir   = Split-Path -Parent $scriptDir

$dataDir   = Join-Path $rootDir "data"
$rawDir    = Join-Path $dataDir "policies_raw"
$processedDir = Join-Path $dataDir "policies_processed"
$sourcesFile = Join-Path $dataDir "policy_sources.txt"

Write-Host "=== Contracts-LLM Policy Pipeline ===" -ForegroundColor Cyan
Write-Host "Root dir     : $rootDir"
Write-Host "Download dir : $DownloadDir"
Write-Host "Raw dir      : $rawDir"
Write-Host "Sources file : $sourcesFile"
Write-Host ""

# 1) Ensure directories exist
foreach ($dir in @($DownloadDir, $rawDir, $processedDir)) {
    if (-not (Test-Path $dir)) {
        Write-Host "[INFO] Creating folder: $dir" -ForegroundColor Yellow
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

# 2) Load list of URLs
if (-not (Test-Path $sourcesFile)) {
    Write-Warning "Sources file not found: $sourcesFile"
    Write-Host "Create it with one PDF URL per line (and no quotes)." -ForegroundColor Yellow
    return
}

$urls = Get-Content $sourcesFile | Where-Object { $_ -and (-not $_.Trim().StartsWith('#')) }

if (-not $urls -or $urls.Count -eq 0) {
    Write-Warning "No URLs found in $sourcesFile (maybe only comments?)."
    return
}

Write-Host "[INFO] Found $($urls.Count) URLs to download." -ForegroundColor Cyan

# 3) Download PDFs
$counter = 0
foreach ($url in $urls) {
    $counter++

    try {
        $uri = [System.Uri]$url
    } catch {
        Write-Warning "Invalid URL (skipping): $url"
        continue
    }

    # Derive filename
    $fileName = [System.IO.Path]::GetFileName($uri.AbsolutePath)
    if ([string]::IsNullOrWhiteSpace($fileName)) {
        $fileName = "policy_$counter.pdf"
    }

    if (-not $fileName.ToLower().EndsWith(".pdf")) {
        $fileName = $fileName + ".pdf"
    }

    $destPath = Join-Path $DownloadDir $fileName

    if (Test-Path $destPath) {
        Write-Host "[SKIP] Already exists: $fileName" -ForegroundColor DarkYellow
        continue
    }

    Write-Host "[DL] $url" -ForegroundColor Green
    Write-Host "    -> $destPath"

    try {
        Invoke-WebRequest -Uri $url -OutFile $destPath -TimeoutSec 180
    } catch {
        Write-Warning "Failed to download $url : $($_.Exception.Message)"
        continue
    }
}

Write-Host ""
Write-Host "[STEP] Copying downloaded PDFs into data\\policies_raw..." -ForegroundColor Cyan

# 4) Copy PDFs to rawDir
$pdfFiles = Get-ChildItem -Path $DownloadDir -Filter *.pdf -File

if (-not $pdfFiles) {
    Write-Warning "No PDF files found in $DownloadDir. Nothing to ingest."
    return
}

foreach ($pdf in $pdfFiles) {
    $dest = Join-Path $rawDir $pdf.Name
    Copy-Item -Path $pdf.FullName -Destination $dest -Force
}

Write-Host "[OK] Copied $($pdfFiles.Count) PDFs to $rawDir" -ForegroundColor Green

# 5) Run ingest_policies.py and build_vector_index.py using the venv Python
$pythonPath = Join-Path $rootDir ".venv\\Scripts\\python.exe"

if (-not (Test-Path $pythonPath)) {
    Write-Warning "Python venv not found at: $pythonPath"
    Write-Host "Make sure your .venv is created in contracts-llm." -ForegroundColor Yellow
    return
}

Write-Host ""
Write-Host "[STEP] Running ingest_policies.py (PDF -> JSON processed)..." -ForegroundColor Cyan
Push-Location $rootDir
try {
    & $pythonPath "ingest_policies.py"
} catch {
    Write-Warning "Error running ingest_policies.py : $($_.Exception.Message)"
}
Pop-Location

Write-Host ""
Write-Host "[STEP] Running build_vector_index.py (build/update embeddings index)..." -ForegroundColor Cyan
Push-Location $rootDir
try {
    & $pythonPath "build_vector_index.py"
} catch {
    Write-Warning "Error running build_vector_index.py : $($_.Exception.Message)"
}
Pop-Location

Write-Host ""
Write-Host "[DONE] Download + ingest + index pipeline finished." -ForegroundColor Green
