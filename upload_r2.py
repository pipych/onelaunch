"""
Upload OneLaunch update to Cloudflare R2.
Creates version.json + ZIP archive of _app/, uploads both.
Usage: python upload_r2.py
"""
import json
import os
import sys
import zipfile
from pathlib import Path

import boto3
from botocore.config import Config

ROOT = Path(__file__).parent.absolute()
R2_BUCKET = "olupdate"
R2_ACCOUNT_ID = "89476ea08498adb1813b3607c5079df7"
R2_ENDPOINT = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
R2_PUBLIC_URL = "https://update.onelaunch.pp.ua"

# Read .env for credentials (optional override)
env_path = ROOT / ".env"
if env_path.exists():
    lines = env_path.read_text().strip().splitlines()
    for line in lines:
        if "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

ACCESS_KEY = os.environ["R2_ACCESS_KEY_ID"]
SECRET_KEY = os.environ["R2_SECRET_ACCESS_KEY"]


def get_version():
    """Extract VERSION from launcher.py"""
    launcher = ROOT / "launcher.py"
    for line in launcher.read_text(encoding='utf-8').splitlines():
        if line.startswith('VERSION = "'):
            return line.split('"')[1]
    return "0.0.0"


def create_update_zip(version: str) -> Path:
    """Zip _app/ directory for upload."""
    app_dir = ROOT / "_app_demo"  # placeholder — use actual built _app
    real_app = ROOT / "dist" / "OneLaunch_App"
    
    if real_app.exists():
        app_dir = real_app
    else:
        print(f"ERROR: {real_app} not found! Build launcher first.")
        sys.exit(1)

    zip_path = ROOT / "dist" / f"OneLaunch_v{version}.zip"
    print(f"Creating {zip_path.name}...")
    
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(str(app_dir)):
            for f in files:
                full = Path(root) / f
                arcname = str(full.relative_to(app_dir))
                zf.write(str(full), arcname)
    
    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"  OK: {size_mb:.1f} MB")
    return zip_path


def create_version_json(version: str, zip_name: str):
    """Create version.json manifest."""
    manifest = {
        "version": version,
        "url": f"{R2_PUBLIC_URL}/{zip_name}",
    }
    path = ROOT / "dist" / "version.json"
    path.write_text(json.dumps(manifest, indent=2))
    print(f"Created {path.name}: {manifest}")
    return path


def upload_to_r2(local_path: Path, key: str):
    """Upload a file to R2."""
    s3 = boto3.client(
        "s3",
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        config=Config(region_name="auto"),
    )
    
    size_mb = local_path.stat().st_size / (1024 * 1024)
    print(f"Uploading {key} ({size_mb:.1f} MB)...")
    
    s3.upload_file(
        str(local_path),
        R2_BUCKET,
        key,
        ExtraArgs={"ContentType": "application/octet-stream"}
    )
    print(f"  OK: {R2_PUBLIC_URL}/{key}")


def main():
    version = get_version()
    print(f"Version: {version}")
    
    # 1. Create update ZIP
    zip_path = create_update_zip(version)
    
    # 2. Create version.json
    vj_path = create_version_json(version, zip_path.name)
    
    # 3. Upload both
    print("\n--- Uploading to R2 ---")
    upload_to_r2(vj_path, "version.json")
    upload_to_r2(zip_path, zip_path.name)
    
    print(f"\nDone! Users on older versions will auto-update to v{version}.")


if __name__ == "__main__":
    main()
