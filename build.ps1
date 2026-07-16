# Build OneLaunch (launcher) + NSIS installer
# Run from: C:\Users\pshen\.openclaw\workspace\onelaunch
$ErrorActionPreference = "Stop"
Push-Location $PSScriptRoot

Write-Host "=== Step 1: Clean previous builds ==="
Remove-Item -Recurse -Force dist, build -ErrorAction SilentlyContinue
Remove-Item OneLaunch*.spec -ErrorAction SilentlyContinue

# ── Build Launcher (onedir, full app) ────────────────────
Write-Host "=== Step 2: Build OneLaunch_App.exe (launcher) ==="
python -m PyInstaller --onedir --noconsole --name OneLaunch_App `
  --icon OneLaunch_icon.ico `
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

$appDir = "dist\OneLaunch_App"
if (-not (Test-Path "$appDir\OneLaunch_App.exe")) {
    Write-Host "ERROR: $appDir\OneLaunch_App.exe not created!" -ForegroundColor Red
    exit 1
}
$launcherSize = (Get-Item "$appDir\OneLaunch_App.exe").Length / 1KB
Write-Host "OneLaunch_App.exe (launcher): $([math]::Round($launcherSize)) KB"

# ── Build Go updater (optional — skip if Go not installed) ──
Write-Host "=== Step 3: Build Go updater ==="
$go = Get-Command go -ErrorAction SilentlyContinue
if ($go) {
    Push-Location "$PSScriptRoot\updater"
    $env:GOOS = "windows"
    $env:CGO_ENABLED = "0"
    go build -ldflags "-s -w -H windowsgui" -o "..\dist\OneLaunch.exe" .
    Pop-Location
    if (Test-Path "dist\OneLaunch.exe") {
        $goSize = (Get-Item "dist\OneLaunch.exe").Length / 1KB
        Write-Host "OneLaunch.exe (updater): $([math]::Round($goSize)) KB"
    } else {
        Write-Host "WARNING: Go build succeeded but output not found" -ForegroundColor Yellow
    }
} else {
    Write-Host "SKIP: Go not installed (build_go_updater.ps1 separately)" -ForegroundColor Yellow
}

# ── Layout: launcher in _app/ ────────────────────────────
Write-Host "=== Step 3: Final layout ==="
$staging = "dist\staging"
Remove-Item -Recurse -Force $staging -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $staging | Out-Null

# Copy Go updater (entry point)
if (Test-Path "dist\OneLaunch.exe") {
    Copy-Item "dist\OneLaunch.exe" "$staging\OneLaunch.exe"
    Write-Host "  Copied OneLaunch.exe (Go updater)"
} else {
    Write-Host "  NOTE: OneLaunch.exe missing — build Go updater first" -ForegroundColor Yellow
}

# Copy launcher as _app/
Copy-Item -Recurse "$appDir" "$staging\_app"

Write-Host "Layout: $staging"
Get-ChildItem $staging -Recurse -Depth 2 | ForEach-Object { $_.FullName.Substring($PSScriptRoot.Length + 1) }

# ── Build NSIS installer ─────────────────────────────────
Write-Host "=== Step 4: Build NSIS installer ==="
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

$setup = "installer\OneLaunch_Setup.exe"
if (Test-Path $setup) {
    $size = (Get-Item $setup).Length / 1MB
    Write-Host "=== DONE ===" -ForegroundColor Green
    Write-Host "  Launcher:   $appDir\"
    Write-Host "  Installer:  $setup ($([math]::Round($size,1)) MB)"
} else {
    Write-Host "ERROR: $setup not found!" -ForegroundColor Red
}
