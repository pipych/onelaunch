"""
OneLaunch Updater вЂ” splash + update check + launch main app
Tiny onefile exe. Always runs first.
"""

import json, os, shutil, subprocess, sys, tempfile, time, zipfile
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.parse import quote

VERSION = "0.2.7"
UPDATE_MANIFEST_URL = "https://update.onelaunch.pp.ua/onelaunch-update.json"

if getattr(sys, 'frozen', False):
    APP_DIR = Path(sys.executable).parent
else:
    APP_DIR = Path(__file__).parent

APP_SUBDIR = APP_DIR / "_app"
LAUNCHER_EXE = APP_SUBDIR / "OneLaunch_App.exe"


def _parse_ver(v):
    try:
        return tuple(int(x) for x in v.split("."))
    except Exception:
        return (0,)


def check_for_updates():
    try:
        r = Request(UPDATE_MANIFEST_URL, headers={"User-Agent": f"OneLaunch-Updater/{VERSION}"})
        with urlopen(r, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8-sig"))
        latest = data.get("version", "")
        url = data.get("url", "")
        if latest and _parse_ver(latest) > _parse_ver(VERSION) and url:
            return True, latest, url
    except Exception:
        pass
    return False, None, None


def download_with_progress(url, dest, splash, new_ver):
    """Download ZIP with progress bar updates to splash window."""
    url = quote(url, safe=':/?#[]@!$&\'()*+,;=')
    r = Request(url, headers={"User-Agent": "OneLaunch-Updater/1.0"})
    with urlopen(r, timeout=60) as resp:
        total = int(resp.headers.get('Content-Length', 0))
        total_mb = total / (1024 * 1024) if total > 0 else 0
        done = 0
        with open(dest, "wb") as f:
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                if total > 0:
                    pct = int(done / total * 100)
                    mb = done / (1024 * 1024)
                    splash.evaluate_js(f"setSplashProgress({pct})")
                    splash.evaluate_js(f"setSplashText('Downloading {new_ver}... {mb:.0f} / {total_mb:.0f} MB')")


def install_update(extract_dir, splash, new_ver):
    """Replace _app/ with extracted files, with progress feedback."""
    splash.evaluate_js(f"setSplashText('Installing {new_ver}...')")
    splash.evaluate_js("setSplashProgress(100)")

    # Count files for progress
    all_files = []
    for root, dirs, files in os.walk(str(extract_dir)):
        for f in files:
            all_files.append(Path(root) / f)
    total_files = len(all_files)

    # Remove old _app
    if APP_SUBDIR.exists():
        try:
            shutil.rmtree(str(APP_SUBDIR), ignore_errors=True)
            time.sleep(0.5)
        except Exception:
            pass

    APP_SUBDIR.mkdir(parents=True, exist_ok=True)

    # Copy files one by one with progress
    for i, src in enumerate(all_files):
        rel = src.relative_to(extract_dir)
        # OneLaunch.exe goes to root, everything else into _app/
        if rel.name == "OneLaunch.exe":
            dst = APP_DIR / "OneLaunch.exe"
        else:
            dst = APP_SUBDIR / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(str(src), str(dst))
        except Exception:
            pass
        if total_files > 0 and i % 50 == 0:
            pct = int(i / total_files * 100)
            splash.evaluate_js(f"setSplashProgress({pct})")
            splash.evaluate_js(f"setSplashText('Installing {new_ver}... {pct}%')")

    splash.evaluate_js("setSplashProgress(100)")
    splash.evaluate_js(f"setSplashText('Installing {new_ver}... 100%')")


def launch_launcher():
    if LAUNCHER_EXE.exists():
        subprocess.Popen(
            [str(LAUNCHER_EXE)], shell=False,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )


def do_update(download_url, new_ver, splash):
    tmp_dir = Path(tempfile.gettempdir())
    zip_path = tmp_dir / "OneLaunch_Update.zip"
    extract_dir = tmp_dir / "OneLaunch_Update"

    try:
        # Phase 1: Download
        splash.evaluate_js(f"setSplashText('Downloading {new_ver}...')")
        splash.evaluate_js("setSplashBar(True)")
        download_with_progress(download_url, str(zip_path), splash, new_ver)

        # Phase 2: Extract
        if extract_dir.exists():
            shutil.rmtree(str(extract_dir), ignore_errors=True)
        extract_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(str(zip_path), 'r') as zf:
            zf.extractall(str(extract_dir))
        zip_path.unlink(missing_ok=True)

        # Phase 3: Install (replace _app)
        install_update(extract_dir, splash, new_ver)

        # Cleanup temp extract dir
        shutil.rmtree(str(extract_dir), ignore_errors=True)

        # Phase 4: Done -- launch new version
        splash.evaluate_js("setSplashText('Done! Starting OneLaunch...')")
        time.sleep(0.5)
        splash.destroy()
        launch_launcher()
        os._exit(0)

    except Exception as e:
        import traceback
        log_path = APP_DIR / "onelaunch-error.log"
        log_path.write_text(f"Update error: {e}\n{traceback.format_exc()}", "utf-8")
        try:
            splash.evaluate_js(f"setSplashText('Error: {str(e)[:50]}')")
            splash.evaluate_js("setSplashProgress(0)")
            time.sleep(3)
            splash.destroy()
        except Exception:
            pass
        # Even on error, try to launch existing launcher
        launch_launcher()
        os._exit(0)


SPLASH_HTML = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0d1114;display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;user-select:none;overflow:hidden;font-family:'Segoe UI',-apple-system,sans-serif}
.logo{font-size:22px;font-weight:800;color:#d4d4d4;letter-spacing:-.5px;margin-bottom:8px}
.version{font-size:11px;color:#4a5568;font-weight:600;letter-spacing:1px;margin-bottom:20px}
.loader{display:flex;gap:4px;margin-bottom:16px}
.loader span{width:6px;height:6px;background:#c0ff00;border-radius:50%;animation:bounce .6s infinite alternate}
.loader span:nth-child(2){animation-delay:.2s}
.loader span:nth-child(3){animation-delay:.4s}
@keyframes bounce{to{transform:translateY(-6px);opacity:.4}}
.status{font-size:12px;color:#6b7280;text-align:center;padding:0 20px;min-height:16px}
.bar-wrap{width:220px;height:4px;background:#14171c;border-radius:50px;margin-top:16px;overflow:hidden;opacity:0;transition:opacity .3s}
.bar-wrap.on{opacity:1}
.bar-fill{width:0;height:100%;background:#c0ff00;border-radius:50px;transition:width .3s}
</style>
</head>
<body>
<div class="logo">OneLaunch</div>
<div class="version" id="ver">v</div>
<div class="loader" id="ldr"><span></span><span></span><span></span></div>
<div class="status" id="status">Checking for updates...</div>
<div class="bar-wrap" id="bar"><div class="bar-fill" id="fill"></div></div>
<script>
window.setSplashText = function(text) {
  document.getElementById('status').textContent = text;
};
window.setSplashBar = function(show) {
  if (show) {
    document.getElementById('bar').classList.add('on');
    document.getElementById('ldr').style.display = 'none';
  }
};
window.setSplashProgress = function(pct) {
  document.getElementById('fill').style.width = pct + '%';
};
window.setSplashVersion = function(v) {
  document.getElementById('ver').textContent = 'v' + v;
};
</script>
</body>
</html>'''


def on_splash_loaded():
    import webview
    splash = webview.windows[0]

    # Show current version
    splash.evaluate_js(f"setSplashVersion('{VERSION}')")

    has_update, new_ver, update_url = check_for_updates()

    if has_update:
        do_update(update_url, new_ver, splash)
        # never reaches here (os._exit)
    else:
        # No update -- launch launcher and exit
        launch_launcher()
        splash.destroy()
        os._exit(0)


if __name__ == "__main__":
    import webview
    splash = webview.create_window(
        "OneLaunch", html=SPLASH_HTML,
        width=360, height=240,
        frameless=True, resizable=False, on_top=True
    )
    webview.start(func=on_splash_loaded)
