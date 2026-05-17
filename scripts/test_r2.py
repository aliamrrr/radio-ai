"""Quick R2 connectivity test — run once to verify credentials."""
import json
import sys
import boto3
from botocore.config import Config

ENDPOINT   = "https://32c7843e1d35d868346f8e24da089b07.r2.cloudflarestorage.com"
KEY_ID     = "515fe5a8fecd38e03a2191232284039d"
SECRET     = "31bf309188a42eb1d1c8d2512eb6f223e0c60a963258342969c21dfb0e35942f"
BUCKET     = "radio-ai"
PUBLIC_URL = "https://pub-792af2e012ff4f0f90fb71e69e11c2f5.r2.dev"

client = boto3.client(
    "s3",
    endpoint_url=ENDPOINT,
    aws_access_key_id=KEY_ID,
    aws_secret_access_key=SECRET,
    region_name="auto",
    config=Config(signature_version="s3v4"),
)

print(f"NOTE: bucket '{BUCKET}' must be created manually in the Cloudflare R2 dashboard.")
print(f"      dash.cloudflare.com -> R2 -> Create bucket -> name: {BUCKET}")
print()

# 1. Upload test file
print("[1/2] Uploading health.json...")
try:
    payload = json.dumps({"status": "ok", "service": "ai-radio"}).encode()
    client.put_object(
        Bucket=BUCKET,
        Key="health.json",
        Body=payload,
        ContentType="application/json",
        CacheControl="no-cache",
    )
    print("      Upload OK.")
except Exception as e:
    print(f"      FAILED: {e}")
    print()
    print("Action required:")
    print("  1. Go to dash.cloudflare.com -> R2 -> Create bucket")
    print(f"     Name: {BUCKET}")
    print("  2. Settings -> Public access -> Enable")
    print(f"  3. Re-run: python scripts/test_r2.py")
    sys.exit(1)

# 2. Read back
print("[2/2] Reading health.json back...")
resp = client.get_object(Bucket=BUCKET, Key="health.json")
data = json.loads(resp["Body"].read())
assert data["status"] == "ok", f"Unexpected: {data}"
print(f"      Read OK: {data}")

print()
print("R2 fully working!")
print(f"Public URL: {PUBLIC_URL}/health.json")
