"""
OneLaunch Updater — splash + tufup update check + launch launcher.
Tiny onefile exe. Always runs first.
"""
import os, subprocess, sys, threading, time
from pathlib import Path

import _update_tuf

VERSION = "0.2.7"

if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).parent
else:
    APP_DIR = Path(__file__).parent

# The launcher lives in _app/ (on Windows: %APPDATA%\OneLaunch\_app\OneLaunch_App.exe)
LAUNCHER_EXE = APP_DIR / "_app" / "OneLaunch_App.exe"


def launch_launcher():
    if LAUNCHER_EXE.exists():
        subprocess.Popen(
            [str(LAUNCHER_EXE)],
            shell=False,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )


SPLASH_HTML = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0d1114;display:flex;flex-direction:column;align-items:center;
  justify-content:center;height:100vh;user-select:none;overflow:hidden;
  font-family:'Segoe UI',-apple-system,sans-serif}
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


def progress_hook_splash(splash):
    """Return a progress hook that updates the splash window."""

    def hook(bytes_downloaded: int, bytes_expected: int):
        if bytes_expected > 0:
            pct = int(bytes_downloaded / bytes_expected * 100)
            mb_down = bytes_downloaded / (1024 * 1024)
            mb_total = bytes_expected / (1024 * 1024)
            splash.evaluate_js(f"setSplashProgress({pct})")
            splash.evaluate_js(f"setSplashText('Downloading... {mb_down:.0f} / {mb_total:.0f} MB')")

    return hook


def on_splash_loaded():
    import webview

    splash = webview.windows[0]
    splash.evaluate_js(f"setSplashVersion('{VERSION}')")

    try:
        _update_tuf.init_for_updater(VERSION)
        splash.evaluate_js("setSplashBar(True)")
        new_version = _update_tuf.check_and_update(
            version=VERSION, progress_hook=progress_hook_splash(splash)
        )

        if new_version:
            splash.evaluate_js(
                f"setSplashText('Updated to {new_version}! Starting...')"
            )
            time.sleep(1.5)
            splash.destroy()
            launch_launcher()
            os._exit(0)
    except ImportError:
        pass  # tufup not installed, just launch
    except Exception as e:
        splash.evaluate_js(f"setSplashText('Error: {str(e)[:50]}')")
        time.sleep(2)

    splash.destroy()
    launch_launcher()
    os._exit(0)


if __name__ == "__main__":
    import webview

    splash = webview.create_window(
        "OneLaunch",
        html=SPLASH_HTML,
        width=360,
        height=240,
        frameless=True,
        resizable=False,
        on_top=True,
    )
    webview.start(func=on_splash_loaded)
