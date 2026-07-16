"""Configure CORS on olskins bucket for skin loading"""
from pathlib import Path
import boto3, json
from botocore.config import Config

ROOT = Path(__file__).parent
env = {}
ep = ROOT / ".env"
if ep.exists():
    for line in ep.read_text().strip().splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()

s3 = boto3.client(
    "s3",
    endpoint_url=f"https://{env['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
    aws_access_key_id=env["R2_ACCESS_KEY_ID"],
    aws_secret_access_key=env["R2_SECRET_ACCESS_KEY"],
    config=Config(region_name="auto"),
)

cors_config = {
    "CORSRules": [
        {
            "AllowedOrigins": ["*"],
            "AllowedMethods": ["GET", "HEAD"],
            "AllowedHeaders": ["*"],
            "MaxAgeSeconds": 3600,
        }
    ]
}

try:
    s3.put_bucket_cors(Bucket="olskins", CORSConfiguration=cors_config)
    print("CORS configured on olskins bucket")
except Exception as e:
    print(f"Error: {e}")
