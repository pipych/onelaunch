# Build OneLaunch.exe + NSIS installer
# Run from: C:\Users\pshen\.openclaw\workspace\onelaunch
$ErrorActionPreference = "Stop"
Push-Location $PSScriptRoot

Write-Host "=== Step 1: Clean previous builds ==="
Remove-Item -Recurse -Force dist, build -ErrorAction SilentlyContinue
Remove-Item *.spec -ErrorAction SilentlyContinue

Write-Host "=== Step 2: Build OneLaunch.exe ==="
python -m PyInstaller --onefile --noconsole --name OneLaunch `
  --hidden-import webview `
  --hidden-import webview.platforms.winforms `
  --hidden-import minecraft_launcher_lib `
  --hidden-import minecraft_launcher_lib.forge `
  --hidden-import minecraft_launcher_lib.install `
  --hidden-import minecraft_launcher_lib.runtime `
  --hidden-import minecraft_launcher_lib.command `
  --collect-all minecraft_launcher_lib `
  --collect-all webview `
  launcher.py

if (-not (Test-Path "dist\OneLaunch.exe")) {
    Write-Host "ERROR: dist\OneLaunch.exe not created!" -ForegroundColor Red
    exit 1
}
Write-Host "OneLaunch.exe built: $((Get-Item 'dist\OneLaunch.exe').Length / 1KB) KB"

Write-Host "=== Step 3: Build NSIS installer ==="
$nsis = Get-Command makensis -ErrorAction SilentlyContinue
if (-not $nsis) {
    $nsis = "${env:ProgramFiles(x86)}\NSIS\makensis.exe"
    if (-not (Test-Path $nsis)) {
        $nsis = "${env:ProgramFiles}\NSIS\makensis.exe"
    }
}
if (-not (Test-Path $nsis)) {
    Write-Host "ERROR: NSIS not found! Install from https://nsis.sourceforge.io/Download" -ForegroundColor Red
    exit 1
}

& $nsis "installer\OneLaunch.nsi"
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: NSIS build failed!" -ForegroundColor Red
    exit 1
}

$setup = "OneLaunch_Setup.exe"
if (Test-Path $setup) {
    $size = (Get-Item $setup).Length / 1MB
    Write-Host "=== DONE: $setup ($([math]::Round($size,1)) MB) ===" -ForegroundColor Green
} else {
    Write-Host "ERROR: $setup not found!" -ForegroundColor Red
}
