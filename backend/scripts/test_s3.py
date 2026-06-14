#!/usr/bin/env python3
"""Quick S3 connectivity test. Run with env vars set:

  IC_S3_BUCKET=testing-245111010944 \
  IC_S3_REGION=ap-south-1 \
  IC_S3_ACCESS_KEY=AKIA... \
  IC_S3_SECRET_KEY=... \
  python3 scripts/test_s3.py
"""
import os
import sys

import boto3
from botocore.config import Config

bucket = os.environ.get("IC_S3_BUCKET", "")
region = os.environ.get("IC_S3_REGION", "us-east-1")
access_key = os.environ.get("IC_S3_ACCESS_KEY", "")
secret_key = os.environ.get("IC_S3_SECRET_KEY", "")

if not all([bucket, access_key, secret_key]):
    print("ERROR: Set IC_S3_BUCKET, IC_S3_ACCESS_KEY, IC_S3_SECRET_KEY")
    sys.exit(1)

print(f"Bucket: {bucket}")
print(f"Region: {region}")

client = boto3.client(
    "s3",
    region_name=region,
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
    config=Config(signature_version="s3v4"),
)

# 1. Upload a test file
test_key = "test/health-check.txt"
print(f"\n1. Uploading test file to s3://{bucket}/{test_key} ...")
client.put_object(
    Bucket=bucket,
    Key=test_key,
    Body=b"Invoice Copilot S3 health check",
    ContentType="text/plain",
)
print("   OK")

# 2. Generate pre-signed URL
print("2. Generating pre-signed URL ...")
url = client.generate_presigned_url(
    "get_object",
    Params={"Bucket": bucket, "Key": test_key},
    ExpiresIn=60,
)
print(f"   URL: {url[:80]}...")

# 3. Fetch the URL
print("3. Fetching pre-signed URL ...")
import urllib.request

resp = urllib.request.urlopen(url)
body = resp.read().decode()
assert body == "Invoice Copilot S3 health check", f"Unexpected: {body}"
print(f"   OK — got: {body}")

# 4. Cleanup
print("4. Cleaning up test file ...")
client.delete_object(Bucket=bucket, Key=test_key)
print("   OK")

print("\nAll S3 checks passed!")
