# Lanza backend y UI en dos ventanas de PowerShell separadas

$backendScript = "C:\Users\Usuario\contracts-ai\contracts-llm\start-backend.ps1"
$uiScript      = "C:\Users\Usuario\contracts-ai\contracts-ui\start-ui.ps1"

Start-Process powershell -ArgumentList "-NoExit","-ExecutionPolicy","Bypass","-File",$backendScript
Start-Process powershell -ArgumentList "-NoExit","-ExecutionPolicy","Bypass","-File",$uiScript
