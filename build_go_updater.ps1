# Build Go updater (OneLaunch.exe)
# Requires: Go 1.21+ installed
# Run from: C:\Users\pshen\.openclaw\workspace\onelaunch
$ErrorActionPreference = "Stop"
Push-Location "$PSScriptRoot\updater"

Write-Host "=== Building Go updater ==="

$go = Get-Command go -ErrorAction SilentlyContinue
if (-not $go) {
    Write-Host "ERROR: Go not found! Install from https://go.dev/dl/" -ForegroundColor Red
    exit 1
}

# Build as Windows GUI app (no console window)
$env:GOOS = "windows"
$env:CGO_ENABLED = "0"

go build -ldflags "-s -w -H windowsgui" -o "..\dist\OneLaunch.exe" .

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Go build failed!" -ForegroundColor Red
    Pop-Location
    exit 1
}

$size = (Get-Item "..\dist\OneLaunch.exe").Length / 1KB
Write-Host "OneLaunch.exe (updater): $([math]::Round($size)) KB"
Pop-Location
