import subprocess, os, sys

os.chdir(r"C:\Users\pshen\.openclaw\workspace\onelaunch")

r = subprocess.run(
    [r"C:\Program Files (x86)\NSIS\makensis.exe", "installer\OneLaunch.nsi"],
    capture_output=True, text=True
)
print("STDOUT:", r.stdout[-500:] if r.stdout else "empty")
print("STDERR:", r.stderr[-500:] if r.stderr else "empty")
print("EXIT:", r.returncode)

if os.path.exists("installer\OneLaunch_Setup.exe"):
    sz = os.path.getsize("installer\OneLaunch_Setup.exe") / 1024 / 1024
    print(f"INSTALLER SIZE: {sz:.1f} MB")
else:
    print("INSTALLER MISSING")
