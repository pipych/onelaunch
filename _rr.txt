"""
OneLaunch Release — set version + full build + git commit & push.
Usage: python release.py [version]
  If no version, prompts interactively.
"""

import re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).parent

COMMIT_FILES = [
    "onelaunch-update.json", "launcher.py", "updater.py",
    "write_nsi.py", "installer/OneLaunch.nsi",
    "build.ps1", "release.py", "set_version.py", ".gitignore",
]

BIN_FILES = ["installer/OneLaunch_Setup.exe"]

GITIGNORE_PATTERNS = [
    "dist/", "build/", "*.spec", "__pycache__/", "*.pyc", ".env",
]

FILES = {
    "onelaunch-update.json": [
        ('"version": "{}"', '"version": "OLD"'),
    ],
    "launcher.py": [
        ('^VERSION = "{}"', 'VERSION = "OLD"'),
    ],
    "updater.py": [
        ('^VERSION = "{}"', 'VERSION = "OLD"'),
    ],
    "write_nsi.py": [
        ('VIProductVersion "{}.0"', 'VIProductVersion "OLD"'),
        ('"FileVersion" "{}"', '"FileVersion" "OLD"'),
        ('"ProductVersion" "{}"', '"ProductVersion" "OLD"'),
    ],
    "installer/OneLaunch.nsi": [
        ('VIProductVersion "{}.0"', 'VIProductVersion "OLD"'),
        ('"FileVersion" "{}"', '"FileVersion" "OLD"'),
        ('"ProductVersion" "{}"', '"ProductVersion" "OLD"'),
    ],
}

ENCODINGS = {"installer/OneLaunch.nsi": "cp1251"}


def get_encoding(fname):
    return ENCODINGS.get(fname, "utf-8")


def detect_current(files, root):
    for fname, patterns in files.items():
        path = root / fname
        if not path.exists():
            continue
        text = path.read_text(encoding=get_encoding(fname))
        for template, _ in patterns:
            old_pattern = template.replace("{}", r"(\d+\.\d+\.\d+)")
            m = re.search(old_pattern, text, re.MULTILINE)
            if m:
                return m.group(1)
    return None


def apply_version(version, files, root):
    for fname, patterns in files.items():
        path = root / fname
        if not path.exists():
            print(f"  SKIP {fname}: not found")
            continue
        enc = get_encoding(fname)
        text = path.read_text(encoding=enc)
        original = text
        for template, _ in patterns:
            old_pattern = template.replace("{}", r"\d+\.\d+\.\d+")
            # Strip regex anchors from the replacement text
            new_text = template.format(version).lstrip('^')
            text = re.sub(old_pattern, new_text, text, flags=re.MULTILINE)
        if text != original:
            path.write_text(text, encoding=enc)
            print(f"  OK   {fname}")
        else:
            print(f"  SAME {fname}")


def git_commit_and_push(version):
    print(f"\n=== Git commit v{version} ===\n")

    gi_path = ROOT / ".gitignore"
    existing = gi_path.read_text().splitlines() if gi_path.exists() else []
    for pat in GITIGNORE_PATTERNS:
        if pat not in existing:
            with open(gi_path, "a") as f:
                f.write(f"\n{pat}")
            print(f"  Added to .gitignore: {pat}")

    files_to_add = []
    for fname in COMMIT_FILES + BIN_FILES:
        path = ROOT / fname
        if path.exists():
            files_to_add.append(fname)

    if not files_to_add:
        print("  No files to commit.")
        return 0

    subprocess.run(["git", "add"] + files_to_add, cwd=str(ROOT), check=True)
    print(f"  Staged: {', '.join(files_to_add)}")

    msg = f"v{version}"
    result = subprocess.run(["git", "commit", "-m", msg], cwd=str(ROOT))
    if result.returncode != 0:
        print("  Nothing to commit (already up to date).")
        return 0

    print("  Pushing to origin...")
    result = subprocess.run(["git", "push"], cwd=str(ROOT))
    if result.returncode == 0:
        print(f"  Pushed v{version} to GitHub.")
    else:
        print("  Push failed! Check git remote.")
        return result.returncode

    return 0


def main():
    current = detect_current(FILES, ROOT) or "?"
    print(f"Current version: {current}")

    if len(sys.argv) > 1:
        new_ver = sys.argv[1].strip()
    else:
        new_ver = input("New version: ").strip()

    if not new_ver:
        print("No version given. Abort.")
        return 1

    if not re.match(r'^\d+\.\d+\.\d+$', new_ver):
        print(f"ERROR: '{new_ver}' is not a valid version (use X.Y.Z).")
        return 1

    # Step 1 — set version
    print(f"\nSetting version: {current} -> {new_ver}\n")
    apply_version(new_ver, FILES, ROOT)

    print("\nRegenerating installer/OneLaunch.nsi...")
    subprocess.run([sys.executable, str(ROOT / "write_nsi.py")], cwd=str(ROOT))

    # Step 2 — build
    print(f"\n=== Building version {new_ver} ===\n")
    result = subprocess.run(
        ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "build.ps1")],
        cwd=str(ROOT)
    )
    if result.returncode != 0:
        print("\nBuild FAILED!")
        return result.returncode

    # Step 3 — git commit + push
    git_rc = git_commit_and_push(new_ver)
    if git_rc != 0:
        print("\nGit push FAILED!")
        return git_rc

    print(f"\n=== Release {new_ver} complete ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
