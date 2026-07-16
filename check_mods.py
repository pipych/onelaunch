"""Check R2 bucket for CustomSkinLoader mod"""
import os
from pathlib import Path
import boto3
from botocore.config import Config

env = {}
ep = Path(__file__).parent / ".env"
if ep.exists():
    for line in ep.read_text().strip().splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()

s3 = boto3.client(
    "s3",
    endpoint_url="https://89476ea08498adb1813b3607c5079df7.r2.cloudflarestorage.com",
    aws_access_key_id=env["R2_ACCESS_KEY_ID"],
    aws_secret_access_key=env["R2_SECRET_ACCESS_KEY"],
    config=Config(region_name="auto"),
)

result = s3.list_objects_v2(
    Bucket="olupdate", Prefix="onehouse-pack-v1/mods/", MaxKeys=200
)

for obj in result.get("Contents", []):
    key = obj["Key"]
    if "customskin" in key.lower() or "skinloader" in key.lower():
        print(f"FOUND: {key} ({obj['Size']} bytes)")
        break
else:
    print("CustomSkinLoader NOT in bucket mods/")
    print("Total mods in bucket:", len(result.get("Contents", [])))
