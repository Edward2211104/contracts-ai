# update-ui-connect-llm.ps1
# Conecta la UI al backend http://127.0.0.1:4050/llm/ask-basic
# y hace backup de contracts-app*.js

$ErrorActionPreference = "Stop"

Write-Host "=== Connecting UI to LLM backend ===" -ForegroundColor Cyan

# 1) Carpeta raíz de la UI
$uiRoot = $PSScriptRoot
if (-not $uiRoot) {
    $uiRoot = (Get-Location).Path
}

# 2) Buscar el archivo real de la UI (contracts-app*.js)
$jsFile = Get-ChildItem -Path $uiRoot -Filter "contracts-app*.js" -File -ErrorAction SilentlyContinue | Select-Object -First 1

if (-not $jsFile) {
    throw "No se encontró ningún archivo 'contracts-app*.js' en $uiRoot"
}

$targetFile = $jsFile.FullName
Write-Host "Usando archivo de UI: $($jsFile.Name)" -ForegroundColor Yellow

# 3) Crear backup
$backupDir = Join-Path $uiRoot "_archive_local"
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null

$timestamp  = Get-Date -Format "yyyyMMdd_HHmmss"
$backupFile = Join-Path $backupDir ("$($jsFile.Name).before_llm_" + $timestamp + ".bak")

Copy-Item $targetFile $backupFile -Force
Write-Host "Backup guardado en: $backupFile" -ForegroundColor Yellow

# 4) Leer el archivo actual
$source = Get-Content $targetFile -Raw

# 5) Patrón: desde 'const sendToAI = async' hasta justo antes de 'const handleSend = async'
$pattern = 'const sendToAI = async[\s\S]*?const handleSend = async'

if ($source -notmatch $pattern) {
    throw "No se pudo localizar el bloque original de sendToAI en $($jsFile.Name). La estructura del archivo ha cambiado."
}

# 6) Nuevo bloque sendToAI que llama a nuestro backend
$newFunc = @'
const sendToAI = async (userMessage, contractContext = "") => {
  try {
    const payload = {
      question: userMessage,
      contractText: contractContext || "",
      extraContext: ""
    };

    const response = await fetch("http://127.0.0.1:4050/llm/ask-basic", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    let data = null;
    try {
      data = await response.json();
    } catch {
      // Si la respuesta no es JSON válido, lo tratamos como error
    }

    if (!response.ok || !data || data.ok === false) {
      const httpInfo = !response.ok ? ` HTTP ${response.status}` : "";
      const detail = data && (data.detail || data.error)
        ? `\n\nServer detail: ${data.detail || data.error}`
        : "";
      throw new Error(`The analysis server reported an error.${httpInfo}${detail}`);
    }

    // Devolvemos solo el texto útil
    return data.answer || "The analysis server did not return an answer.";
  } catch (err) {
    console.error("Error calling analysis server:", err);
    const msg = err && err.message ? err.message : String(err);
    return `Could not reach the analysis server at http://127.0.0.1:4050/llm/ask-basic.\n\n${msg}`;
  }
};

const handleSend = async () =>
'@

# 7) Aplicar reemplazo
$updated = [regex]::Replace($source, $pattern, $newFunc)

# 8) Guardar cambios
Set-Content -Path $targetFile -Value $updated -Encoding UTF8

Write-Host "contracts-app.js actualizado correctamente." -ForegroundColor Green
Write-Host "Si algo va mal, puedes restaurar desde: $backupFile" -ForegroundColor Yellow
Write-Host "===============================================" -ForegroundColor Cyan
