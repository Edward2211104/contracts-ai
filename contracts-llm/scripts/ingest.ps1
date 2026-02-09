param(
  [string]\ = "..\data\raw_pdfs"
)
$ErrorActionPreference = 'Stop'
$ROOT = (Split-Path -Parent (Split-Path -Parent $PSCommandPath))
$venv = Join-Path $ROOT '.venv\Scripts\Activate.ps1'
. $venv

Write-Host "
[ingest] OCR (if needed) ..." -ForegroundColor Cyan
$raw = Join-Path $ROOT 'data\raw_pdfs'
$ocr = Join-Path $ROOT 'data\ocr_pdfs'
$txt = Join-Path $ROOT 'data\ocr_text'
New-Item -ItemType Directory -Force -Path $ocr, $txt | Out-Null

Get-ChildItem -Path $raw -Filter *.pdf | ForEach-Object {
  $in = $_.FullName
  $outPdf = Join-Path $ocr $_.Name
  $outTxt = Join-Path $txt ($_.BaseName + '.txt')
  if (!(Test-Path $outPdf)) {
    try { ocrmypdf --force-ocr "$in" "$outPdf" | Out-Null } catch {}
  }
  if (!(Test-Path $outTxt)) {
    try {
      # extract text from OCR'd PDF
      python - << 'PY'
import sys, fitz, pathlib
pdf = pathlib.Path(sys.argv[1])
out = pathlib.Path(sys.argv[2])
doc = fitz.open(pdf)
text = []
for p in doc:
    text.append(p.get_text('text'))
out.write_text("\n".join(text), encoding='utf-8', errors='ignore')
PY
      "$outPdf" "$outTxt"
    } catch {}
  }
}

Write-Host "
[ingest] Clause extraction ..." -ForegroundColor Cyan
python "$ROOT\src\extract\extractor.py"

Write-Host "
[ingest] Build FAISS index ..." -ForegroundColor Cyan
python "$ROOT\src\retriever\indexer.py"

Write-Host "
[ingest] DONE" -ForegroundColor Green
