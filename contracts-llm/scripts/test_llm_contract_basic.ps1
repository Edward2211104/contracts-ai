param(
    [string]$Question = "I am a tenant under a commercial lease. The landlord is asking me to start paying full rent even though repairs after water damage are still ongoing. What key issues should I check in my lease, and what are some options I might have?"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "`n[TEST] POST /llm/ask-basic ..." -ForegroundColor Cyan

$body = @{
    question    = $Question
    context     = "General contract analysis. The app may also have an indexed knowledge base of contracts and policies."
    has_contract = $false
} | ConvertTo-Json

try {
    $response = Invoke-WebRequest `
        -Uri "http://127.0.0.1:4050/llm/ask-basic" `
        -Method POST `
        -ContentType "application/json" `
        -Body $body

    Write-Host "`n[RESPONSE RAW]:" -ForegroundColor Yellow
    $response.Content
}
catch {
    Write-Host "`n[ERR] Llamada a /llm/ask-basic falló:" -ForegroundColor Red
    $ex = $_.Exception
    if ($ex.Response -ne $null) {
        $resp = $ex.Response
        $reader = New-Object System.IO.StreamReader($resp.GetResponseStream())
        $bodyText = $reader.ReadToEnd()
        Write-Host "HTTP $($resp.StatusCode) $($resp.StatusDescription)" -ForegroundColor Red
        Write-Host $bodyText
    }
    else {
        Write-Host $ex.Message -ForegroundColor Red
    }
}
