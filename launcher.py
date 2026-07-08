"""
OneLaunch — Minecraft Forge 1.20.1 launcher
UI: HTML/CSS in native Windows window via pywebview (no browser)
"""

import hashlib, json, os, secrets, shutil, subprocess, sys, threading, time
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import urlopen, Request
from urllib.parse import quote, urlencode, parse_qs, urlparse

import minecraft_launcher_lib as mcl

# ── Config ──────────────────────────────────────────────

GAME_DIR = Path(__file__).parent / ".minecraft"
MC_VERSION = "1.20.1"
MODPACK_URL = "https://pub-61c15faa68244ff5afc5cf17a0054122.r2.dev/onehouse-pack-v1/manifest.json"

_forge_version = None
_pack_manifest = None

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
        if "java.exe" in fs: return str(Path(r) / "java.exe")
    jh = os.environ.get("JAVA_HOME")
    if jh:
        p = Path(jh) / "bin" / "java.exe"
        if p.exists(): return str(p)
    for base in [r"C:\Program Files\Eclipse Adoptium", r"C:\Program Files\Java"]:
        p = Path(base)
        if p.exists():
            for d in p.iterdir():
                if d.is_dir():
                    e = d / "bin" / "java.exe"
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

def download_file(url, dest):
    url = quote(url, safe=':/?#[]@!$&\'()*+,;=')
    r = Request(url, headers={"User-Agent": "OneLaunch/1.0"})
    with urlopen(r) as resp:
        with open(dest, "wb") as f: shutil.copyfileobj(resp, f)

def sync_modpack():
    fs = fetch_manifest()
    s = {"downloaded": 0, "skipped": 0, "errors": 0}
    for f in fs:
        dest = GAME_DIR / f["path"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            try:
                if sha256_file(dest) == f["sha256"]: s["skipped"] += 1; continue
            except: pass
        try:
            download_file(f["url"], dest); s["downloaded"] += 1
        except: s["errors"] += 1
    return s

def launch_game(username, uuid_str, access_token):
    java = get_java() or install_java()
    fv = find_installed_forge() or get_forge_version()
    if not find_installed_forge():
        install_forge(); fv = find_installed_forge()
    opts = {"username": username, "uuid": uuid_str, "token": access_token,
            "executablePath": java, "jvmArguments": ["-Xmx2G", "-Xms512M"],
            "launcherName": "OneLaunch", "launcherVersion": "1.0"}
    cmd = mcl.command.get_minecraft_command(fv, str(GAME_DIR), opts)
    subprocess.Popen(cmd, cwd=str(GAME_DIR), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

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
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  font-family:'Segoe UI',-apple-system,sans-serif;
  background:#090b0e;color:#d4d4d4;
  display:flex;flex-direction:column;align-items:center;
  height:100vh;user-select:none;overflow:hidden;
}
.ta{text-align:center;padding-top:60px}
.ta h1{font-size:32px;font-weight:800;color:#d4d4d4;letter-spacing:-.5px}
.ta p{font-size:12px;color:#6b7280;margin-top:4px}
.s{flex:1}
.sbtn{
  background:#14171c;color:#6b7280;border:none;border-radius:50px;
  padding:10px 32px;font-size:13px;font-weight:700;cursor:pointer;transition:.2s;margin-bottom:12px
}
.sbtn:hover{background:#1c2430}
.sbtn.ready{color:#c0ff00}
.pa{display:none;flex-direction:column;align-items:center;width:320px;margin-bottom:12px}
.pa.on{display:flex}
.pt{width:100%;height:4px;background:#14171c;border-radius:50px;overflow:hidden}
.pf{width:0;height:100%;background:#c0ff00;border-radius:50px;transition:width .3s}
.ptx{font-size:11px;color:#6b7280;margin-top:6px}
.bb{width:100%;background:#14171c;display:flex;align-items:flex-end;justify-content:space-between;padding:18px 28px}
.nl{font-size:9px;font-weight:700;color:#6b7280;text-transform:uppercase;letter-spacing:.5px}
.ni{
  background:#090b0e;color:#d4d4d4;border:1px solid #1f2937;
  border-radius:50px;padding:10px 18px;width:150px;font-size:14px;
  font-weight:700;text-align:center;outline:none;transition:border-color .2s
}
.ni:focus{border-color:#c0ff00}
.pb{
  background:#c0ff00;color:#090b0e;border:none;border-radius:50px;
  padding:14px 48px;font-size:16px;font-weight:800;cursor:pointer;
  letter-spacing:1px;transition:.2s
}
.pb:hover{background:#96cc00;transform:scale(1.02)}
.pb:active{transform:scale(.98)}
.pb:disabled{background:#374151;color:#6b7280;cursor:default;transform:none}
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
</style>
</head>
<body>
<div class="ta"><h1>OneLaunch</h1><p>Minecraft 1.20.1 + Forge</p></div>
<div class="s"></div>
<button class="sbtn" id="sb" onclick="showStatus()">📊  Статус</button>
<div class="pa" id="pa"><div class="pt"><div class="pf" id="pf"></div></div><div class="ptx" id="ptx"></div></div>
<div class="s"></div>
<div class="bb">
  <div><span class="nl">Никнейм</span><br><input class="ni" id="ni" value="Player" maxlength="16"></div>
  <button class="pb" id="pb" onclick="doPlay()">ИГРАТЬ</button>
</div>
<div class="ov" id="ov"><div class="oc"><h3>⚙  Статус</h3><div id="sl"></div><button class="cl" onclick="showStatus()">Закрыть</button></div></div>
<script>
var installing = false;

async function showStatus() {
  var ov = document.getElementById('ov');
  if (ov.classList.contains('show')) { ov.classList.remove('show'); return; }
  var data = await pywebview.api.get_status();
  var h = '';
  [
    ['Java 17', data.java],
    ['Minecraft 1.20.1', data.vanilla],
    ['Forge', data.forge],
    ['Modpack', data.mods > 0 ? data.mods + ' модов' : 'не установлен']
  ].forEach(function(i) {
    var ok = (typeof i[1] === 'boolean' && i[1]) || (typeof i[1] === 'number' && i[1] > 0);
    h += '<div class="sr"><span><span class="d ' + (ok ? 'ok' : 'fl') + '">●</span><span class="ll">' + i[0] + '</span></span><span class="v">' + (typeof i[1] === 'boolean' ? (i[1] ? '✓' : '✗') : i[1]) + '</span></div>';
  });
  document.getElementById('sl').innerHTML = h;
  ov.classList.add('show');
  updateStatusBtn();
}

function updateStatusBtn() {
  pywebview.api.get_status().then(function(data) {
    var b = document.getElementById('sb');
    if (data.java && data.vanilla && data.forge) {
      b.textContent = '📊  Готово'; b.classList.add('ready');
    } else {
      b.textContent = '📊  Статус'; b.classList.remove('ready');
    }
  });
}

function setProgress(p, t) {
  document.getElementById('pa').classList.add('on');
  document.getElementById('pf').style.width = p + '%';
  if (t) document.getElementById('ptx').textContent = t;
}

function doPlay() {
  if (installing) return;
  var nick = document.getElementById('ni').value.trim();
  if (nick.length < 3) { alert('Никнейм 3-16 символов'); return; }
  installing = true;
  var btn = document.getElementById('pb');
  btn.disabled = true; btn.textContent = '...';
  setProgress(5, 'Подготовка...');
  pywebview.api.install_and_launch(nick);
}

// Called from Python to update progress
window._setProgress = function(p, t) { setProgress(p, t); };
window._onComplete = function(err) {
  installing = false;
  var btn = document.getElementById('pb');
  btn.disabled = false; btn.textContent = 'ИГРАТЬ';
  if (err) { setProgress(0, 'Ошибка: ' + err); setTimeout(function(){document.getElementById('pa').classList.remove('on')}, 5000); }
  else { setProgress(100, 'Игра запущена!'); setTimeout(function(){document.getElementById('pa').classList.remove('on')}, 4000); }
  updateStatusBtn();
};

updateStatusBtn();
</script>
</body>
</html>'''


# ── API for pywebview ───────────────────────────────────

class Api:
    def get_status(self):
        return get_status()

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
                sync_modpack()
                progress(95, 'Запуск игры...')
                launch_game(nick, offline_uuid(nick), "***")
                w.evaluate_js("_onComplete('')")
            except Exception as e:
                w.evaluate_js(f"_onComplete('{str(e)}')")
        threading.Thread(target=run, daemon=True).start()


# ── Main ─────────────────────────────────────────────────

if __name__ == "__main__":
    GAME_DIR.mkdir(parents=True, exist_ok=True)
    import webview
    api = Api()
    window = webview.create_window(
        "OneLaunch", html=HTML, js_api=api,
        width=460, height=400, resizable=False
    )
    webview.start(debug=False)
