"""Replace all mod URLs in manifest from pub-X.r2.dev to modpack.onelaunch.pp.ua"""
import json
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
MANIFEST_KEY = "onehouse-pack-v1/manifest.json"
OLD_DOMAIN = "pub-61c15faa68244ff5afc5cf17a0054122.r2.dev"
NEW_DOMAIN = "modpack.onelaunch.pp.ua"

s3 = boto3.client(
    "s3",
    endpoint_url=f"https://{env['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
    aws_access_key_id=env["R2_ACCESS_KEY_ID"],
    aws_secret_access_key=env["R2_SECRET_ACCESS_KEY"],
    config=Config(region_name="auto"),
)

# Download manifest
print("Downloading manifest...")
resp = s3.get_object(Bucket=BUCKET, Key=MANIFEST_KEY)
manifest = json.loads(resp["Body"].read())
print(f"Total mods: {len(manifest['mods'])}")

# Replace URLs
replaced = 0
for mod in manifest["mods"]:
    if OLD_DOMAIN in mod["url"]:
        mod["url"] = mod["url"].replace(OLD_DOMAIN, NEW_DOMAIN)
        replaced += 1

print(f"Replaced {replaced} URLs")

# Upload updated manifest
print("Uploading updated manifest...")
s3.put_object(
    Bucket=BUCKET,
    Key=MANIFEST_KEY,
    Body=json.dumps(manifest, indent=4, ensure_ascii=False).encode("utf-8"),
    ContentType="application/json",
)
print("Done!")
