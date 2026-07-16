"""Add existing CustomSkinLoader to manifest"""
import json, hashlib, os
from pathlib import Path
import boto3
from botocore.config import Config

ROOT = Path(__file__).parent

env = {}
ep = ROOT / ".env"
if ep.exists():
    for line in ep.read_text().strip().splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()

BUCKET = "onelaunch-mods"
PREFIX = "onehouse-pack-v1"
MANIFEST_KEY = f"{PREFIX}/manifest.json"
MOD_FILENAME = "CustomSkinLoader_Universal-15.0.1.jar"
MOD_KEY = f"{PREFIX}/mods/{MOD_FILENAME}"
PUBLIC_URL = "https://modpack.onelaunch.pp.ua"

s3 = boto3.client(
    "s3",
    endpoint_url=f"https://{env['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
    aws_access_key_id=env["R2_ACCESS_KEY_ID"],
    aws_secret_access_key=env["R2_SECRET_ACCESS_KEY"],
    config=Config(region_name="auto"),
)

# 1. Get existing mod file and compute SHA256
print("=== Computing SHA256 of existing mod ===")
mod_obj = s3.get_object(Bucket=BUCKET, Key=MOD_KEY)
mod_data = mod_obj["Body"].read()
mod_sha256 = hashlib.sha256(mod_data).hexdigest()
print(f"Size: {len(mod_data)} bytes, SHA256: {mod_sha256}")

# 2. Download manifest
print("\n=== Updating manifest ===")
manifest_resp = s3.get_object(Bucket=BUCKET, Key=MANIFEST_KEY)
manifest = json.loads(manifest_resp["Body"].read())

# Check if already in manifest
paths = [m["path"] for m in manifest["mods"]]
if f"mods/{MOD_FILENAME}" in paths:
    print("Already in manifest!")
else:
    manifest["mods"].append({
        "path": f"mods/{MOD_FILENAME}",
        "url": f"{PUBLIC_URL}/{MOD_KEY}",
        "sha256": mod_sha256,
    })
    manifest["mods"].sort(key=lambda m: m["path"].lower())

    s3.put_object(
        Bucket=BUCKET,
        Key=MANIFEST_KEY,
        Body=json.dumps(manifest, indent=4, ensure_ascii=False).encode("utf-8"),
        ContentType="application/json",
    )
    print(f"OK: added CustomSkinLoader, total mods: {len(manifest['mods'])}")

print("\n=== Done! ===")
