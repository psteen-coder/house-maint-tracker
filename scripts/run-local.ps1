# One-shot: create venv if needed, install deps, serve the built UI on :8000
# Run from anywhere:  powershell -ExecutionPolicy Bypass -File .\scripts\run-local.ps1
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..\backend")

$py = Join-Path (Get-Location) ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Host "Creating .venv ..."
    python -m venv .venv
    if (-not (Test-Path $py)) {
        throw "python -m venv failed. Install Python 3.12+ from python.org and tick Add python.exe to PATH."
    }
}

Write-Host "Installing packages (this can take a minute) ..."
& $py -m pip install --upgrade pip
& $py -m pip install -r requirements.txt

Write-Host ""
Write-Host "Open http://127.0.0.1:8000"
Write-Host "Login: patrick@1944dinius.local / adminpass"
Write-Host "Leave this window open. Ctrl+C stops the server."
Write-Host ""
& $py -m uvicorn app.main:app --host 127.0.0.1 --port 8000
