"""
OneLaunch — Minecraft Forge 1.20.1 launcher
UI: HTML/CSS in native Windows window via pywebview (no browser)
"""

import hashlib, json, os, shutil, subprocess, sys, threading, time, base64
from io import BytesIO
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import urlopen, Request
from urllib.parse import quote, urlencode, parse_qs, urlparse

import minecraft_launcher_lib as mcl

# ── R2 Skins upload ───────────────────────────────────

try:
    import boto3
    from PIL import Image
    HAS_SKIN_UPLOAD = True
except ImportError:
    HAS_SKIN_UPLOAD = False

R2_ACCOUNT_ID = "89476ea08498adb1813b3607c5079df7"
R2_SKINS_BUCKET = "olskins"
R2_SKINS_ENDPOINT = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

# ── Config ──────────────────────────────────────────────

# Root dir: when frozen, use parent of _app/ (where OneLaunch.exe lives)
# When running from source, use the script's directory
if getattr(sys, 'frozen', False):
    _exe_dir = Path(sys.executable).parent
    ROOT_DIR = _exe_dir.parent if _exe_dir.name == '_app' else _exe_dir
else:
    ROOT_DIR = Path(__file__).parent

GAME_DIR = ROOT_DIR / ".minecraft"
CONFIG_PATH = ROOT_DIR / "onelaunch.json"
MC_VERSION = "1.20.1"
MODPACK_URL = "https://modpack.onelaunch.pp.ua/onehouse-pack-v1/manifest.json"

_forge_version = None
_pack_manifest = None

VERSION = "0.4.6"
def load_config():
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {"nickname": ""}

def save_config(cfg):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

# ── Backend ─────────────────────────────────────────────

def get_forge_version():
    global _forge_version
    if _forge_version is None:
        vs = mcl.forge.list_forge_versions()
        m = [v for v in vs if v.startswith("1.20.1-")]
        _forge_version = m[-1] if m else mcl.forge.find_forge_version("1.20.1")
    return _forge_version

def find_installed_forge():
    d = GAME_DIR / "versions"
    if not d.exists(): return None
    for e in d.iterdir():
        if e.is_dir() and e.name.startswith("1.20.1-forge-"):
            if any(f.suffix == ".jar" for f in e.iterdir()): return e.name
    return None

def offline_uuid(n):
    h = hashlib.md5(f"OfflinePlayer:{n}".encode()).hexdigest()
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"

def get_java():
    for r, _, fs in os.walk(str(GAME_DIR / "runtime")):
        for exe in ("javaw.exe", "java.exe"):
            if exe in fs: return str(Path(r) / exe)
    jh = os.environ.get("JAVA_HOME")
    if jh:
        for exe in ("javaw.exe", "java.exe"):
            p = Path(jh) / "bin" / exe
            if p.exists(): return str(p)
    for base in [r"C:\Program Files\Eclipse Adoptium", r"C:\Program Files\Java"]:
        p = Path(base)
        if p.exists():
            for d in p.iterdir():
                if d.is_dir():
                    for exe in ("javaw.exe", "java.exe"):
                        e = d / "bin" / exe
                        if e.exists(): return str(e)
    return None

def install_java():
    mcl.runtime.install_jvm_runtime("java-runtime-gamma", str(GAME_DIR), callback={
        "setStatus": lambda t: None, "setProgress": lambda p: None, "setMax": lambda m: None})

def install_mc():
    GAME_DIR.mkdir(parents=True, exist_ok=True)
    mcl.install.install_minecraft_version(MC_VERSION, str(GAME_DIR), callback={
        "setStatus": lambda t: None, "setProgress": lambda p: None, "setMax": lambda m: None})

def install_forge():
    global _forge_version
    fv = get_forge_version()
    mcl.forge.install_forge_version(fv, str(GAME_DIR), callback={
        "setStatus": lambda t: None, "setProgress": lambda p: None, "setMax": lambda m: None})
    _forge_version = fv

def fetch_manifest():
    global _pack_manifest
    if _pack_manifest: return _pack_manifest
    r = Request(MODPACK_URL, headers={"User-Agent": "OneLaunch/1.0"})
    with urlopen(r) as resp:
        d = json.loads(resp.read().decode("utf-8-sig"))
    fs = []
    for cat in ("mods", "configs", "overrides"):
        for e in d.get(cat, []):
            fs.append({"path": e["path"], "url": e["url"], "sha256": e["sha256"]})
    _pack_manifest = fs
    return fs

def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(8192), b""): h.update(c)
    return h.hexdigest()

def download_file(url, dest, timeout=30):
    url = quote(url, safe=':/?#[]@!$&\'()*+,;=')
    r = Request(url, headers={"User-Agent": "OneLaunch/1.0"})
    with urlopen(r, timeout=timeout) as resp:
        with open(dest, "wb") as f: shutil.copyfileobj(resp, f)

def sync_modpack(progress_cb=None):
    """Sync modpack with parallel downloads and progress tracking."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    fs = fetch_manifest()
    total = len(fs)
    s = {"downloaded": 0, "skipped": 0, "errors": 0, "total": total}
    
    # Separate into to_download vs already-have
    to_download = []
    for f in fs:
        dest = GAME_DIR / f["path"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            try:
                if sha256_file(dest) == f["sha256"]:
                    s["skipped"] += 1
                    continue
            except:
                pass
        to_download.append(f)
    
    if progress_cb:
        progress_cb(s["skipped"], total, "Проверка модов...")
    
    if not to_download:
        return s
    
    # Parallel download (max 6 concurrent)
    completed = 0
    dl_count = len(to_download)
    
    def _dl_one(item):
        nonlocal completed
        try:
            dest = GAME_DIR / item["path"]
            download_file(item["url"], dest, timeout=60)
            completed += 1
            if progress_cb:
                progress_cb(s["skipped"] + completed, total,
                    f'Моды: {s["skipped"] + completed}/{total}')
            return ("ok", item["path"])
        except Exception as e:
            completed += 1
            return ("err", str(e))
    
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(_dl_one, f): f for f in to_download}
        for future in as_completed(futures):
            status, info = future.result()
            if status == "ok":
                s["downloaded"] += 1
            else:
                s["errors"] += 1
    
    return s

def launch_game(username, uuid_str, access_token):
    cfg = load_config()
    ram_mb = cfg.get("ram_mb", 2048)
    java = get_java() or install_java()
    fv = find_installed_forge() or get_forge_version()
    if not find_installed_forge():
        install_forge(); fv = find_installed_forge()
    opts = {"username": username, "uuid": uuid_str, "token": access_token,
            "executablePath": java, "jvmArguments": [f"-Xmx{ram_mb}M", "-Xms512M"],
            "launcherName": "OneLaunch", "launcherVersion": "1.0"}
    cmd = mcl.command.get_minecraft_command(fv, str(GAME_DIR), opts)
    filtered = []
    for arg in cmd:
        if arg.startswith('-Xmx') or arg.startswith('-Xms'):
            continue
        filtered.append(arg)
    filtered[1:1] = [f'-Xmx{ram_mb}M', '-Xms512M']
    cmd = filtered
    subprocess.Popen(cmd, cwd=str(GAME_DIR),
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)

def get_status():
    j = get_java() is not None
    v = (GAME_DIR / "versions" / MC_VERSION / f"{MC_VERSION}.jar").exists()
    f = find_installed_forge() is not None
    m = 0
    if (GAME_DIR / "mods").exists(): m = len(list((GAME_DIR / "mods").rglob("*.jar")))
    return {"java": j, "vanilla": v, "forge": f, "mods": m, "forge_version": find_installed_forge() or ""}


# ── HTML ────────────────────────────────────────────────

HTML = r'''<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<script src="https://cdn.jsdelivr.net/npm/skinview3d@3/bundles/skinview3d.bundle.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
button{-webkit-app-region:no-drag;app-region:no-drag}
/* ── Title bar ── */
.titlebar{position:fixed;top:0;right:0;z-index:200;height:36px;display:flex;align-items:center;justify-content:flex-end;padding:0 8px}
.titlebar-version{position:fixed;top:0;left:0;z-index:201;padding:11px 16px;font-size:10px;font-weight:600;color:#4a5568;font-family:'Segoe UI',sans-serif;letter-spacing:1px}
.titlebar-title{display:none}
.titlebar-btns{display:flex;gap:2px;-webkit-app-region:no-drag;app-region:no-drag}
.tb-btn{background:none;border:none;cursor:pointer;width:28px;height:28px;display:flex;align-items:center;justify-content:center;border-radius:50%;color:#6b7280;transition:all .15s}
.tb-btn:hover{background:#1f2937;color:#d4d4d4}
.tb-btn.tb-close:hover{background:#ef4444;color:#fff}
.tb-btn svg{width:14px;height:14px}
body{font-family:'Segoe UI',-apple-system,sans-serif;background:#090b0e;color:#d4d4d4;height:100vh;user-select:none;overflow:hidden;display:flex;flex-direction:column;will-change:transform}
/* ── Main area: skin viewer ── */
.main-area{flex:1;display:flex;min-height:0}
.left-panel{flex:1;display:flex;align-items:center;justify-content:center;background:#090b0e;position:relative;min-width:0}
#skin-canvas{width:100%;height:100%}
/* ── Skin upload (right side, no background) ── */
.skin-panel{display:flex;flex-direction:column;align-items:center;justify-content:flex-start;padding:20px 16px 0;flex-shrink:0;gap:6px;background:#090b0e}
.sk-btn{background:#1a1d22;color:#d4d4d4;border:1px solid #2d3138;border-radius:50px;padding:10px 24px;font-size:13px;font-weight:600;cursor:pointer;transition:all .2s;white-space:nowrap}
.sk-btn:hover{background:#20242a;border-color:#c0ff00}
.sk-btn:disabled{opacity:.7;cursor:not-allowed}
.***{display:none;justify-content:center}
.sk-spinner{display:none;width:16px;height:16px;border:2px solid #2d3138;border-top-color:#c0ff00;border-radius:50%;animation:sk-spin .6s linear infinite}
.***.on .sk-spinner{display:block}
@keyframes sk-spin{to{transform:rotate(360deg)}}
.sk-status{font-size:11px;color:#6b7280;text-align:center;line-height:1.4;max-width:160px}
/* ── Bottom bar ── */
.bottom-bar{display:flex;align-items:center;padding:0 36px 30px;flex-shrink:0;background:#090b0e}
.bottom-left{flex:1;display:flex;justify-content:flex-start;align-items:center}
.bottom-center{flex-shrink:0;display:flex;flex-direction:column;align-items:center}
.bottom-right{flex:1;display:flex;justify-content:flex-end;align-items:center}
/* ── Nickname ── */
.ni{background:#090b0e;color:#d4d4d4;border:1.5px solid #1f2937;border-radius:50px;padding:10px 18px;width:200px;font-size:14px;font-weight:700;text-align:center;outline:none;transition:border-color .2s}
.ni:focus{border-color:#96cc00}
@keyframes pulse-border{0%,100%{border-color:#1f2937}50%{border-color:#c0ff00}}
.ni:placeholder-shown{animation:pulse-border 2s ease-in-out infinite}
.ni:placeholder-shown:focus{animation:none;border-color:#c0ff00}
/* ── Play button ── */
.pb{background:#c0ff00;color:#090b0e;border:none;border-radius:50px;padding:14px 52px;font-size:16px;font-weight:800;cursor:pointer;letter-spacing:1px;transition:.2s}
.pb:hover{background:#96cc00;transform:scale(1.02)}
.pb:active{transform:scale(.98)}
.pb:disabled{background:#374151;color:#6b7280;cursor:default;transform:none}
/* ── Progress bar (absolute, centered overlay) ── */
.pa{display:none;position:fixed;inset:0;z-index:150;justify-content:center;align-items:center;background:rgba(9,11,14,.85);flex-direction:column;gap:10px}
.pa.on{display:flex}
.pt{width:320px;height:4px;background:#14171c;border-radius:50px;overflow:hidden}
.pf{width:0;height:100%;background:#c0ff00;border-radius:50px;transition:width .3s}
.ptx{font-size:12px;color:#6b7280}
/* ── Icon buttons ── */
.bb-row{display:flex;gap:10px;align-items:center}
.bbtn{background:none;border:none;cursor:pointer;padding:8px;color:#6b7280;transition:color .2s,transform .2s}
.bbtn:hover{color:#c0ff00;transform:scale(1.1)}
.bbtn.ready{color:#c0ff00}
.bbtn svg{width:20px;height:20px;display:block}
[data-tooltip]{position:relative}
[data-tooltip]:hover::after{content:attr(data-tooltip);position:absolute;bottom:calc(100% + 8px);left:50%;transform:translateX(-50%);background:rgba(20,23,28,.95);color:#d4d4d4;font-size:11px;font-weight:600;padding:6px 14px;border-radius:12px;border:1px solid rgba(192,255,0,.2);white-space:nowrap;pointer-events:none;z-index:999;opacity:1;transition:opacity .2s;box-shadow:0 4px 16px rgba(0,0,0,.5)}
[data-tooltip]:not(:hover)::after{opacity:0}
/* ── Overlays ── */
.ov{display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:100;justify-content:center;align-items:center}
.ov.show{display:flex}
.oc{background:#14171c;border:1px solid #1f2937;border-radius:24px;padding:32px;width:340px;animation:pop .2s}
@keyframes pop{from{transform:scale(.9);opacity:0}to{transform:scale(1);opacity:1}}
.oc h3{font-size:16px;color:#c0ff00;margin-bottom:16px}
.sr{display:flex;justify-content:space-between;align-items:center;padding:6px 0;font-size:13px}
.sr .d{font-size:10px;margin-right:8px}
.sr .ok{color:#c0ff00}.sr .fl{color:#ef4444}
.sr .ll{color:#d4d4d4}.sr .v{color:#6b7280;font-weight:600}
.cl{background:#c0ff00;color:#090b0e;border:none;border-radius:50px;padding:10px 40px;margin-top:20px;font-size:13px;font-weight:700;cursor:pointer;width:100%}
.cl:hover{background:#96cc00}
/* ── Settings overlay ── */
.sov{display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:101;justify-content:center;align-items:center}
.sov.show{display:flex}
.sov-c{background:#14171c;border:1px solid #1f2937;border-radius:24px;padding:28px 28px 24px;width:380px;animation:pop .2s;position:relative}
.sov-c h3{font-size:16px;color:#c0ff00;margin-bottom:20px}
.sov-c label{display:block;font-size:11px;color:#6b7280;margin-bottom:8px;text-transform:uppercase;letter-spacing:.5px;font-weight:700}
.sov-c .ram-row{display:flex;align-items:center;gap:12px;margin-bottom:6px}
.sov-c .ram-inp{background:#090b0e;color:#d4d4d4;border:1.5px solid #1f2937;border-radius:12px;padding:8px 0;width:56px;font-size:15px;font-weight:700;text-align:center;outline:none;transition:border-color .2s}
.sov-c .ram-inp:focus{border-color:#96cc00}
.sov-c .ram-slider{flex:1;-webkit-appearance:none;appearance:none;height:6px;background:#1f2937;border-radius:50px;outline:none;cursor:pointer}
.sov-c .ram-slider::-webkit-slider-thumb{-webkit-appearance:none;appearance:none;width:18px;height:18px;background:#c0ff00;border-radius:50%;cursor:pointer;transition:transform .15s}
.sov-c .ram-slider::-webkit-slider-thumb:hover{transform:scale(1.2)}
.sov-c .ram-labels{display:flex;justify-content:space-between;font-size:10px;color:#6b7280;margin-bottom:22px;padding:0 2px}
.sov-c .sov-btns{display:flex;gap:8px}
.sov-c .btn-save{flex:1;background:#c0ff00;color:#090b0e;border:none;border-radius:50px;padding:10px 20px;font-size:13px;font-weight:700;cursor:pointer;transition:background .2s}
.sov-c .btn-save:hover{background:#96cc00}
.sov-c .btn-cancel{flex:1;background:#1f2937;color:#d4d4d4;border:none;border-radius:50px;padding:10px 20px;font-size:13px;font-weight:700;cursor:pointer;transition:background .2s}
.sov-c .btn-cancel:hover{background:#374151}
.sov-c .close-x{position:absolute;top:10px;right:14px;background:none;border:none;color:#6b7280;font-size:20px;cursor:pointer;padding:2px 6px;line-height:1;transition:color .2s}
.sov-c .close-x:hover{color:#c0ff00}
</style>
</head>
<body>
<div class="titlebar">
  <span class="titlebar-version">v__VERSION__</span>
  <span class="titlebar-title"></span>
  <div class="titlebar-btns">
    <button class="tb-btn" onclick="pywebview.api.minimize_window()" title="Свернуть">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M5 12h14"/></svg>
    </button>
    <button class="tb-btn tb-close" onclick="pywebview.api.close_window()" title="Закрыть">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
    </button>
  </div>
</div>
<div class="main-area">
  <div class="left-panel">
    <canvas id="skin-canvas"></canvas>
  </div>
  <div class="skin-panel">
    <button class="sk-btn" id="skBtn" onclick="uploadSkin()">Загрузить скин</button>
    <div class="***" id="skSpinner"><div class="sk-spinner"></div></div>
    <div class="sk-status" id="skStatus">Выберите PNG-файл скина</div>
  </div>
</div>
<div class="pa" id="pa">
  <div class="pt"><div class="pf" id="pf"></div></div>
  <div class="ptx" id="ptx"></div>
</div>
<div class="bottom-bar">
  <div class="bottom-left">
    <input class="ni" id="ni" value="__NICKNAME__" placeholder="Введите ник" maxlength="16">
  </div>
  <div class="bottom-center">
    <button class="pb" id="pb" onclick="doPlay()">ИГРАТЬ</button>
  </div>
  <div class="bottom-right">
    <div class="bb-row">
      <button class="bbtn" id="mfb" onclick="openMcFolder()" data-tooltip="Папка Minecraft">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.93a2 2 0 0 1-1.66-.9l-.82-1.2A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13c0 1.1.9 2 2 2Z"/></svg>
      </button>
      <button class="bbtn" id="sb" onclick="showStatus()" data-tooltip="Статус">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>
      </button>
      <button class="bbtn" id="settingsBtn" onclick="toggleSettings()" data-tooltip="Настройки">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>
      </button>
    </div>
  </div>
</div>
<!-- Status overlay -->
<div class="ov" id="ov">
  <div class="oc">
    <h3>⚙ Статус</h3>
    <div id="sl"></div>
    <button class="cl" onclick="closeOverlay('ov')">Закрыть</button>
  </div>
</div>
<!-- Settings overlay -->
<div class="sov" id="sov" onclick="if(event.target===this)closeOverlay('sov')">
  <div class="sov-c">
    <button class="close-x" onclick="closeOverlay('sov')">&times;</button>
    <h3>⚙ Настройка ОЗУ</h3>
    <label>Выделить памяти (ГБ)</label>
    <div class="ram-row">
      <input class="ram-inp" id="ramInp" type="number" min="1" max="12" oninput="onRamInput()">
      <input class="ram-slider" id="ramSlider" type="range" min="1" max="12" step="1" oninput="onRamSlider()">
    </div>
    <div class="ram-labels"><span>1 ГБ</span><span>12 ГБ</span></div>
    <div class="sov-btns">
      <button class="btn-cancel" onclick="closeOverlay('sov')">Отмена</button>
      <button class="btn-save" onclick="saveRam()">Сохранить</button>
    </div>
  </div>
</div>
<script>
var installing = false;
var _nickTimer = null;
var skinViewer;
var grayTemplate = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==";

(function(){
  var ni = document.getElementById('ni');
  ni.addEventListener('input', function(){
    clearTimeout(_nickTimer);
    var nick = ni.value.trim();
    _nickTimer = setTimeout(function(){
      pywebview.api.save_nickname(nick);
      if (nick) loadSkinFromR2(nick);
    }, 600);
  });
})();

// ── Skin Viewer ──
function initSkinViewer() {
  var canvas = document.getElementById('skin-canvas');
  skinViewer = new skinview3d.SkinViewer({
    canvas: canvas,
    width: 300,
    height: 500,
    skin: grayTemplate,
  });
  skinViewer.playerObject.skin.leftLeg.visible = false;
  skinViewer.playerObject.skin.rightLeg.visible = false;
  // Camera: look at upper body (head + torso)
  skinViewer.camera.position.set(0, 32, 42);
  skinViewer.controls.target.set(0, 28, 0);
  skinViewer.playerObject.rotation.y = Math.PI * 0.65;
  skinViewer.controls.enableZoom = false;
  skinViewer.controls.enableRotate = false;
  skinViewer.controls.minPolarAngle = 1.2;
  skinViewer.controls.maxPolarAngle = 1.8;
}

function loadSkinPreview(base64Data) {
  if (skinViewer) {
    var dataUri = "data:image/png;base64," + base64Data;
    skinViewer.loadSkin(dataUri);
    // Persist to localStorage
    try { localStorage.setItem('onel_skin', dataUri); } catch(e) {}
  }
}

// Load persisted skin on startup (cache fallback)
function loadPersistedSkin() {
  try {
    var saved = localStorage.getItem('onel_skin');
    if (saved && skinViewer) skinViewer.loadSkin(saved);
  } catch(e) {}
}

// Auto-load skin from R2 by nickname
function loadSkinFromR2(nick) {
  if (!nick || !skinViewer) return;
  var url = 'https://skins.onelaunch.pp.ua/skins/' + encodeURIComponent(nick) + '.png?t=' + Date.now();
  var img = new Image();
  img.crossOrigin = 'anonymous';
  img.onload = function() {
    // Convert to data URI to avoid WebGL CORS issues
    try {
      var c = document.createElement('canvas');
      c.width = img.width; c.height = img.height;
      c.getContext('2d').drawImage(img, 0, 0);
      var dataUri = c.toDataURL('image/png');
      skinViewer.loadSkin(dataUri);
      localStorage.setItem('onel_skin', dataUri);
    } catch(e) {
      // Fallback: try direct URL (works with CORS headers)
      skinViewer.loadSkin(url);
    }
  };
  img.onerror = function() {
    loadPersistedSkin();
  };
  img.src = url;
}

function uploadSkin() {
  var btn = document.getElementById('skBtn');
  btn.disabled = true;
  document.getElementById('skSpinner').classList.add('on');
  setSkinStatus('Выбор файла...');
  pywebview.api.select_and_upload().catch(function(err){
    setSkinStatus('Ошибка', true);
    enableSkinButton();
  });
}

function setSkinStatus(text, isError) {
  var el = document.getElementById('skStatus');
  el.innerText = text;
  el.style.color = isError ? '#ef4444' : '#6b7280';
}

function enableSkinButton() {
  var btn = document.getElementById('skBtn');
  btn.disabled = false;
  document.getElementById('skSpinner').classList.remove('on');
}

// ── Window controls ──
function openMcFolder() { pywebview.api.open_minecraft_folder(); }
function closeOverlay(id) { var el = document.getElementById(id); if (el) el.classList.remove('show'); resetStatusBtn(); }

function resetStatusBtn() {
  var b = document.getElementById('sb');
  if (!b) return;
  pywebview.api.get_status().then(function(d){ b.classList.toggle('ready', d.java && d.vanilla && d.forge); });
}

async function showStatus() {
  var ov = document.getElementById('ov');
  if (ov.classList.contains('show')) { closeOverlay('ov'); return; }
  var data = await pywebview.api.get_status();
  var h = '';
  [['Java 17', data.java], ['Minecraft 1.20.1', data.vanilla], ['Forge', data.forge],
   ['Modpack', data.mods > 0 ? data.mods + ' модов' : 'не установлен']].forEach(function(i) {
    var ok = (typeof i[1] === 'boolean' && i[1]) || (typeof i[1] === 'number' && i[1] > 0);
    h += '<div class="sr"><span><span class="d ' + (ok ? 'ok' : 'fl') + '">●</span><span class="ll">' + i[0] + '</span></span><span class="v">' + (typeof i[1] === 'boolean' ? (i[1] ? '✓' : '✗') : i[1]) + '</span></div>';
  });
  document.getElementById('sl').innerHTML = h;
  ov.classList.add('show');
  pywebview.api.get_status().then(function(d){ document.getElementById('sb').classList.toggle('ready', d.java && d.vanilla && d.forge); });
}

// ── Settings / RAM ──
function onRamInput() { var v = Math.max(1, Math.min(12, parseInt(document.getElementById('ramInp').value) || 1)); document.getElementById('ramInp').value = v; document.getElementById('ramSlider').value = v; }
function onRamSlider() { document.getElementById('ramInp').value = document.getElementById('ramSlider').value; }

async function toggleSettings() {
  var sov = document.getElementById('sov');
  if (sov.classList.contains('show')) { closeOverlay('sov'); return; }
  try {
    var mb = await pywebview.api.get_ram_setting();
    var gb = Math.max(1, Math.min(12, Math.round(mb / 1024)));
    document.getElementById('ramInp').value = gb; document.getElementById('ramSlider').value = gb;
  } catch(e) { document.getElementById('ramInp').value = 2; document.getElementById('ramSlider').value = 2; }
  sov.classList.add('show');
}

function saveRam() {
  var gb = Math.max(1, Math.min(12, parseInt(document.getElementById('ramInp').value) || 1));
  document.getElementById('ramInp').value = gb; document.getElementById('ramSlider').value = gb;
  pywebview.api.save_ram_setting(gb * 1024).then(function(){ closeOverlay('sov'); });
}

// ── Play ──
function setProgress(p, t) { document.getElementById('pa').classList.add('on'); document.getElementById('pf').style.width = p + '%'; if (t) document.getElementById('ptx').textContent = t; }

function doPlay() {
  if (installing) return;
  var nick = document.getElementById('ni').value.trim();
  if (nick.length < 1) { alert('Введите никнейм'); return; }
  installing = true;
  var btn = document.getElementById('pb'); btn.disabled = true; btn.textContent = '...';
  setProgress(5, 'Подготовка...');
  pywebview.api.install_and_launch(nick);
}

window._setProgress = function(p, t) { setProgress(p, t); };
window._onComplete = function(err) {
  installing = false;
  var btn = document.getElementById('pb'); btn.disabled = false; btn.textContent = 'ИГРАТЬ';
  if (err) { setProgress(0, 'Ошибка: ' + err); setTimeout(function(){document.getElementById('pa').classList.remove('on')}, 5000); }
  else { setProgress(100, 'Игра запущена!'); setTimeout(function(){document.getElementById('pa').classList.remove('on')}, 4000); }
  pywebview.api.get_status().then(function(d){ document.getElementById('sb').classList.toggle('ready', d.java && d.vanilla && d.forge); });
};

// ── Init ──
initSkinViewer();
// Auto-load skin by nickname, fallback to localStorage cache
var initNick = document.getElementById('ni').value.trim();
if (initNick) { loadSkinFromR2(initNick); } else { loadPersistedSkin(); }
pywebview.api.get_status().then(function(d){ document.getElementById('sb').classList.toggle('ready', d.java && d.vanilla && d.forge); });

document.addEventListener('mousedown', function(e) {
  if (e.target.closest('.tb-btn') || e.target.closest('.bottom-bar') || e.target.closest('button') || e.target.tagName === 'INPUT') return;
  pywebview.api.start_drag();
});
</script>
</body>
</html>'''


# ── API for pywebview ───────────────────────────────────

class Api:
    def __init__(self):
        self.window = None
        self._s3_client = None

    def _get_s3(self):
        if self._s3_client is None and HAS_SKIN_UPLOAD:
            # R2 credentials from .env (loaded in __main__ before Api init)
            access_key = os.environ.get("R2_ACCESS_KEY_ID", "")
            secret_key = os.environ.get("R2_SECRET_ACCESS_KEY", "")
            if not access_key or not secret_key:
                return None
            self._s3_client = boto3.client(
                "s3",
                endpoint_url=R2_SKINS_ENDPOINT,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name="auto",
            )
        return self._s3_client

    def get_status(self):
        return get_status()

    def open_minecraft_folder(self):
        import subprocess, sys
        folder = str(GAME_DIR)
        if sys.platform == "win32":
            subprocess.Popen(["explorer", folder], shell=False)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", folder])
        else:
            subprocess.Popen(["xdg-open", folder])

    def start_drag(self):
        import ctypes
        ctypes.windll.user32.ReleaseCapture()
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        ctypes.windll.user32.SendMessageW(hwnd, 0xA1, 2, 0)

    def minimize_window(self):
        import webview as _wv
        w = _wv.active_window()
        if w: w.minimize()

    def move_win(self, dx: int, dy: int):
        import webview as _wv
        w = _wv.active_window()
        if w:
            x = w.x + dx
            y = w.y + dy
            w.move(x, y)

    def close_window(self):
        import webview as _wv
        w = _wv.active_window()
        if w: w.destroy()

    def get_nickname(self):
        return load_config().get("nickname", "")

    def save_nickname(self, nick: str):
        cfg = load_config()
        cfg["nickname"] = nick
        save_config(cfg)

    def get_ram_setting(self):
        return load_config().get("ram_mb", 2048)

    def save_ram_setting(self, ram_mb: int):
        cfg = load_config()
        cfg["ram_mb"] = int(ram_mb)
        save_config(cfg)

    # ── Skin upload ─────────────────────────────────────

    def select_and_upload(self):
        """Open file dialog, preview instantly, upload in background."""
        import webview as _wv
        win = _wv.active_window()
        if not HAS_SKIN_UPLOAD:
            win.evaluate_js("setSkinStatus('boto3/Pillow не установлены', true); enableSkinButton();")
            return

        # Use tkinter file dialog — more reliable than pywebview's create_file_dialog
        from tkinter import Tk, filedialog
        root = Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        file_path = filedialog.askopenfilename(
            title='Выберите скин (64x64 или 64x32 PNG)',
            filetypes=[('PNG изображения', '*.png'), ('Все файлы', '*.*')]
        )
        root.destroy()
        if not file_path:
            win.evaluate_js("setSkinStatus('Выбор отменён'); enableSkinButton();")
            return
        try:
            with Image.open(file_path) as img:
                w, h = img.size
                if (w, h) not in ((64, 64), (64, 32)):
                    win.evaluate_js(
                        f"setSkinStatus('Неверное разрешение ({w}x{h}). Разрешено: 64x64 или 64x32', true); enableSkinButton();"
                    )
                    return
                img = img.convert("RGBA")
                buf = BytesIO()
                img.save(buf, format="PNG")
                img_bytes = buf.getvalue()
                img_b64 = base64.b64encode(img_bytes).decode("utf-8")

            win.evaluate_js(f"loadSkinPreview('{img_b64}')")
            win.evaluate_js("setSkinStatus('Загрузка в R2...')")

            nickname = load_config().get("nickname", "player")
            # Capture win reference for thread safety
            _win_ref = win
            threading.Thread(
                target=self._upload_to_r2,
                args=(img_bytes, nickname, _win_ref),
                daemon=True,
            ).start()

        except Exception as e:
            win.evaluate_js(f"setSkinStatus('Ошибка: {e}', true); enableSkinButton();")

    def _upload_to_r2(self, img_bytes: bytes, nickname: str, win):
        """Upload skin to R2 in background thread. Reports status via JS."""
        try:
            s3 = self._get_s3()
            if s3 is None:
                ak = os.environ.get('R2_ACCESS_KEY_ID', '')
                sk = os.environ.get('R2_SECRET_ACCESS_KEY', '')
                if not _env_loaded:
                    msg = f'Файл .env не найден в {ROOT_DIR}'
                elif not ak or not sk:
                    missing = 'ACCESS_KEY' if not ak else 'SECRET_KEY'
                    msg = f'В .env нет {missing}'
                else:
                    msg = 'Нет доступа к R2 (проверьте boto3)'
                win.evaluate_js(
                    f"setSkinStatus('{msg}', true); enableSkinButton();"
                )
                return

            object_key = f"skins/{nickname}.png"
            s3.upload_fileobj(
                BytesIO(img_bytes),
                R2_SKINS_BUCKET,
                object_key,
                ExtraArgs={"ContentType": "image/png"},
            )
            win.evaluate_js(
                f"setSkinStatus('Скин загружен!\\nskins.onelaunch.pp.ua/skins/{nickname}.png'); enableSkinButton();"
            )
        except ImportError:
            win.evaluate_js(
                "setSkinStatus('boto3 не установлен', true); enableSkinButton();"
            )
        except Exception as e:
            from botocore.exceptions import ClientError, EndpointConnectionError, NoCredentialsError
            msg = str(e)
            if isinstance(e, NoCredentialsError):
                msg = "Нет ключей R2 — проверьте .env в корне папки"
            elif isinstance(e, EndpointConnectionError):
                msg = "Нет интернета или R2 недоступен"
            elif isinstance(e, ClientError):
                code = getattr(e, 'response', {}).get('Error', {}).get('Code', '')
                if code == 'NoSuchBucket':
                    msg = "Бакет olskins не найден"
                elif code == 'AccessDenied':
                    msg = "Нет доступа к бакету — проверьте ключи"
                elif code == 'InvalidArgument':
                    msg = "Ошибка R2: неверные параметры запроса (проверьте .env)"
                else:
                    msg = f"Ошибка R2: {code or e}"
            win.evaluate_js(
                f"setSkinStatus('{msg}', true); enableSkinButton();"
            )

    def install_and_launch(self, nick: str):
        import webview
        w = webview.active_window()
        def run():
            try:
                def progress(p, t): w.evaluate_js(f"_setProgress({p},'{t}')")
                progress(10, 'Установка Java 17...')
                if not get_java(): install_java()
                progress(30, 'Загрузка Minecraft...')
                if not (GAME_DIR / "versions" / MC_VERSION / f"{MC_VERSION}.jar").exists(): install_mc()
                progress(50, 'Установка Forge...')
                if not find_installed_forge(): install_forge()
                progress(75, 'Синхронизация модпака...')
                def mod_progress(done, total, text):
                    pct = 75 + int((done / total) * 18) if total > 0 else 75
                    w.evaluate_js(f"_setProgress({pct},'{text}')")
                sync_modpack(mod_progress)
                progress(95, 'Запуск игры...')
                launch_game(nick, offline_uuid(nick), "***")
                w.evaluate_js("_onComplete('')")
                import webview as _wv
                def _delayed_exit():
                    time.sleep(10)
                    os._exit(0)
                threading.Thread(target=_delayed_exit, daemon=True).start()
            except Exception as e:
                w.evaluate_js(f"_onComplete('{str(e)}')")
        threading.Thread(target=run, daemon=True).start()


# ── Main ─────────────────────────────────────────────────

if __name__ == "__main__":
    GAME_DIR.mkdir(parents=True, exist_ok=True)

    # Load .env for R2 credentials
    # ROOT_DIR is already set to the right place (next to OneLaunch.exe / _app/)
    env_path = ROOT_DIR / ".env"
    _env_loaded = False
    if env_path.exists():
        for line in env_path.read_text(encoding='utf-8').strip().splitlines():
            if '=' in line and not line.startswith('#'):
                k, v = line.split('=', 1)
                os.environ[k.strip()] = v.strip()  # force override, not setdefault
        _env_loaded = True

    config = load_config()
    saved_nickname = config.get("nickname", "")

    import webview
    api = Api()
    html_with_nick = HTML.replace('__NICKNAME__', saved_nickname).replace('__VERSION__', VERSION)
    window = webview.create_window(
        "OneLaunch", html=html_with_nick, js_api=api,
        width=1280, height=720, resizable=False, frameless=True, easy_drag=False,
        background_color='#090b0e'
    )
    api.window = window
    webview.start(debug=False)
