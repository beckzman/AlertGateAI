# AIOps Backend Start-Skript
# Ausführen aus dem 'backend/' Verzeichnis: .\start.ps1
Write-Host "Starte AIOps Backend auf http://localhost:8000 ..." -ForegroundColor Cyan

$appDir = "$PSScriptRoot\app"
$env:PYTHONPATH = $appDir

Set-Location -Path $appDir
python -m uvicorn main:app --reload --port 8000
