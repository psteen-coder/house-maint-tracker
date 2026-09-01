# Run from backend\:  powershell -ExecutionPolicy Bypass -File .\run.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$py = Join-Path (Get-Location) ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Host "Creating .venv ..."
    python -m venv .venv
}
Write-Host "Installing packages ..."
& $py -m pip install --upgrade pip
& $py -m pip install -r requirements.txt
Write-Host ""
Write-Host "Open http://127.0.0.1:8000"
Write-Host "Login: patrick@1944dinius.local / adminpass"
Write-Host ""
& $py -m uvicorn app.main:app --host 127.0.0.1 --port 8000
