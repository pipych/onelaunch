"""
Set version across all OneLaunch files.
Usage: python set_version.py [version]
  If no version given, prompts interactively.
"""

import re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).parent

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

ENCODINGS = {
    "installer/OneLaunch.nsi": "cp1251",
}


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

    print(f"\nSetting version: {current} -> {new_ver}\n")
    apply_version(new_ver, FILES, ROOT)

    print("\nRegenerating installer/OneLaunch.nsi...")
    subprocess.run([sys.executable, str(ROOT / "write_nsi.py")], cwd=str(ROOT))

    print(f"\nDone. Version is now {new_ver}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
