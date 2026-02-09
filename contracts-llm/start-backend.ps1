# Arranca el backend LLM de Contracts-AI
Set-Location "C:\Users\Usuario\contracts-ai\contracts-llm"
if (Test-Path ".\.venv\Scripts\Activate.ps1") {
    . .\.venv\Scripts\Activate.ps1
}
python .\simple_backend.py
