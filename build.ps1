# Build OneLaunch (updater + launcher) + NSIS installer
# Run from: C:\Users\pshen\.openclaw\workspace\onelaunch
$ErrorActionPreference = "Stop"
Push-Location $PSScriptRoot

Write-Host "=== Step 1: Clean previous builds ==="
Remove-Item -Recurse -Force dist, build -ErrorAction SilentlyContinue
Remove-Item OneLaunch*.spec -ErrorAction SilentlyContinue

# ── Build Updater (tiny onefile exe) ─────────────────────
Write-Host "=== Step 2: Build OneLaunch.exe (updater) ==="
python -m PyInstaller --onefile --noconsole --name OneLaunch `
  --icon OneLaunch_icon.ico `
  --hidden-import webview `
  --hidden-import webview.platforms.winforms `
  --collect-all webview `
  updater.py

if (-not (Test-Path "dist\OneLaunch.exe")) {
    Write-Host "ERROR: dist\OneLaunch.exe not created!" -ForegroundColor Red
    exit 1
}
Write-Host "OneLaunch.exe (updater): $([math]::Round((Get-Item 'dist\OneLaunch.exe').Length / 1KB)) KB"

# ── Build Launcher (onedir, full app) ────────────────────
Write-Host "=== Step 3: Build OneLaunch_App.exe (launcher) ==="
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

# ── Layout: updater at root, launcher in _app/ ──────────
Write-Host "=== Step 4: Final layout ==="
$staging = "dist\staging"
Remove-Item -Recurse -Force $staging -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $staging | Out-Null

# Copy updater
Copy-Item "dist\OneLaunch.exe" "$staging\OneLaunch.exe"

# Copy launcher as _app/
Copy-Item -Recurse "$appDir" "$staging\_app"

# ── Include trusted root.json (if tufup repo exists) ────
$rootSrc = "tufup_repo\repository\metadata\root.json"
if (Test-Path $rootSrc) {
    Write-Host "  Including root.json from tufup repo"
    Copy-Item $rootSrc "$staging\_app\root.json" -Force
    Copy-Item $rootSrc "$staging\root.json" -Force
    # Also copy to dist for dev testing
    Copy-Item $rootSrc "$appDir\root.json" -ErrorAction SilentlyContinue
} else {
    Write-Host "  NOTE: No root.json (run repo_init.py + repo_add_bundle.py after build)" -ForegroundColor Yellow
}

Write-Host "Layout: $staging"
Get-ChildItem $staging -Recurse -Depth 2 | ForEach-Object { $_.FullName.Substring($PSScriptRoot.Length + 1) }

# ── Build NSIS installer ─────────────────────────────────
Write-Host "=== Step 5: Build NSIS installer ==="
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
    Write-Host "  Updater:    dist\OneLaunch.exe"
    Write-Host "  Launcher:   $appDir\"
    Write-Host "  Installer:  $setup ($([math]::Round($size,1)) MB)"
    Write-Host ""
    Write-Host "  Next: run release.py to generate TUF targets + upload to R2"
} else {
    Write-Host "ERROR: $setup not found!" -ForegroundColor Red
}
