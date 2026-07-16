import subprocess, sys, os, shutil, hashlib, json

os.chdir(r"C:\Users\pshen\.openclaw\workspace\onelaunch")

# Clean
for d in ["dist\\OneLaunch_App", "build\\OneLaunch_App", "dist\\staging"]:
    if os.path.exists(d): shutil.rmtree(d, ignore_errors=True)
for f in ["OneLaunch_App.spec", "dist\\OneLaunch_Update.zip", "installer\\OneLaunch_Setup.exe"]:
    if os.path.exists(f): os.remove(f)

# Build launcher
print("Building launcher...")
r = subprocess.run([
    sys.executable, "-m", "PyInstaller",
    "--onedir", "--noconsole", "--name", "OneLaunch_App",
    "--icon", "OneLaunch_icon.ico",
    "--hidden-import", "webview",
    "--hidden-import", "webview.platforms.winforms",
    "--hidden-import", "minecraft_launcher_lib",
    "--hidden-import", "minecraft_launcher_lib.forge",
    "--hidden-import", "minecraft_launcher_lib.install",
    "--hidden-import", "minecraft_launcher_lib.runtime",
    "--hidden-import", "minecraft_launcher_lib.command",
    "--collect-all", "minecraft_launcher_lib",
    "--collect-all", "webview",
    "launcher.py"
], capture_output=True, text=True)
if r.returncode != 0:
    print("BUILD FAILED", r.stderr[-500:])
    sys.exit(1)
print("Launcher built")

# Staging
os.makedirs("dist\\staging", exist_ok=True)
shutil.copy2("dist\\OneLaunch.exe", "dist\\staging\\OneLaunch.exe")
shutil.copytree("dist\\OneLaunch_App", "dist\\staging\\_app")

# ZIP
import zipfile
zipf = zipfile.ZipFile("dist\\OneLaunch_Update.zip", 'w', zipfile.ZIP_DEFLATED)
for root, dirs, files in os.walk("dist\\staging\\_app"):
    for fn in files:
        fp = os.path.join(root, fn)
        ap = os.path.relpath(fp, "dist\\staging\\_app")
        zipf.write(fp, ap)
zipf.close()

# SHA256
with open("dist\\OneLaunch_Update.zip", "rb") as f:
    sha = hashlib.sha256(f.read()).hexdigest()
sz = os.path.getsize("dist\\OneLaunch_Update.zip")

# NSIS
r = subprocess.run([r"C:\Program Files (x86)\NSIS\makensis.exe", "installer\\OneLaunch.nsi"], capture_output=True, text=True)
if r.returncode != 0:
    print("NSIS FAILED", r.stderr[-500:])
    sys.exit(1)

# Manifests
with open("onelaunch-update.json", "w") as f:
    json.dump({"version":"0.2.1","url":"https://pub-f6e5d69d8dfd4ec194b0ebc7b4c3de96.r2.dev/OneLaunch_Update.zip","size":sz,"sha256":sha}, f, indent=2)
with open("update-manifest.json", "w") as f:
    json.dump({"latest_version":"0.2.1","update_url":"https://pub-f6e5d69d8dfd4ec194b0ebc7b4c3de96.r2.dev/OneLaunch_Update.zip","setup_url":"https://pub-f6e5d69d8dfd4ec194b0ebc7b4c3de96.r2.dev/OneLaunch_Setup.exe","check_interval_hours":6}, f, indent=2)

# Sizes
exe1 = os.path.getsize("dist\\OneLaunch.exe")/1e6
exe2 = os.path.getsize("dist\\OneLaunch_App\\OneLaunch_App.exe")/1e6
setup = os.path.getsize("installer\\OneLaunch_Setup.exe")/1e6
zips = sz/1e6

print(f"Done: Updater={exe1:.1f}MB Launcher={exe2:.1f}MB ZIP={zips:.1f}MB Setup={setup:.1f}MB SHA256={sha[:12]}...")
