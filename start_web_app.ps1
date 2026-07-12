$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host "Starting Lead Generator at http://127.0.0.1:8765"
Write-Host "Keep this window open while using the website."
Write-Host ""

python web_app.py
