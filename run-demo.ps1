# run-demo.ps1 - start Legal Ground locally and expose it with a Cloudflare quick tunnel.
#
# Prereqs (one time):
#   1) Package installed in venv:   venv\Scripts\python.exe -m pip install -e ".[dev]"
#   2) cloudflared installed:        winget install --id Cloudflare.cloudflared
#   3) AWS creds available (you ran 'aws configure').
#
# Usage:
#   .\run-demo.ps1                       # uses region us-east-1
#   .\run-demo.ps1 -Region us-west-2     # override region
#
# The Cloudflare tunnel prints a public https://<random>.trycloudflare.com URL.
# Share that link. Press Ctrl+C here to stop the tunnel; close the web window to
# stop the server. Bedrock is only billed while it is running.

param(
    [string]$Region = "us-east-1",
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
$repo = $PSScriptRoot
$webExe = Join-Path $repo "venv\Scripts\legal-ground-web.exe"

if (-not (Test-Path $webExe)) {
    Write-Host "ERROR: legal-ground-web not found at $webExe" -ForegroundColor Red
    Write-Host "Install the package first by running this in the repo folder:" -ForegroundColor Yellow
    Write-Host '    venv\Scripts\python.exe -m pip install -e ".[dev]"' -ForegroundColor Yellow
    exit 1
}

# Find cloudflared: prefer PATH, then fall back to common install locations
# (winget MSI does not always add it to PATH until you reopen the terminal).
$cloudflared = $null
$cmd = Get-Command cloudflared -ErrorAction SilentlyContinue
if ($cmd) {
    $cloudflared = $cmd.Source
} else {
    $candidates = @(
        (Join-Path $env:ProgramFiles "cloudflared\cloudflared.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "cloudflared\cloudflared.exe")
    )
    $candidates += (Get-ChildItem -Path (Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages") -Recurse -Filter "cloudflared*.exe" -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName)
    $cloudflared = $candidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
}

if (-not $cloudflared) {
    Write-Host "ERROR: cloudflared not found." -ForegroundColor Red
    Write-Host "Install it:  winget install --id Cloudflare.cloudflared" -ForegroundColor Yellow
    Write-Host "Then CLOSE this window, open a NEW PowerShell, and run the script again." -ForegroundColor Yellow
    exit 1
}

Write-Host "Starting Legal Ground web app on http://127.0.0.1:$Port (region $Region)..." -ForegroundColor Cyan
$env:LG_PORT = "$Port"
Start-Process -FilePath $webExe -ArgumentList "--aws-region", $Region -WorkingDirectory $repo -WindowStyle Normal

Start-Sleep -Seconds 4
Write-Host "Opening Cloudflare quick tunnel..." -ForegroundColor Cyan
Write-Host "Look for the https://<something>.trycloudflare.com line below - that is your shareable link." -ForegroundColor Green
Write-Host ""

& $cloudflared tunnel --url "http://localhost:$Port"
