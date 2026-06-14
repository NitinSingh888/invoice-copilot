#!/usr/bin/env python3
"""Upload real invoice PDFs to S3 and generate the samples JSON.

Usage:
  IC_S3_BUCKET=testing-245111010944 \
  IC_S3_REGION=ap-south-1 \
  IC_S3_ACCESS_KEY=... \
  IC_S3_SECRET_KEY=... \
  python3 scripts/upload_sample_invoices.py /tmp/invoices_100/

Outputs: data/real_samples.json — used by the /samples endpoint.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path

import boto3
from botocore.config import Config

PDF_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/invoices_100")
OUTPUT = Path(__file__).resolve().parent.parent / "data" / "real_samples.json"
S3_PREFIX = "samples"
MAX = 100

bucket = os.environ["IC_S3_BUCKET"]
region = os.environ.get("IC_S3_REGION", "ap-south-1")

client = boto3.client(
    "s3",
    region_name=region,
    endpoint_url=f"https://s3.{region}.amazonaws.com",
    aws_access_key_id=os.environ["IC_S3_ACCESS_KEY"],
    aws_secret_access_key=os.environ["IC_S3_SECRET_KEY"],
    config=Config(signature_version="s3v4"),
)

pdfs = sorted(PDF_DIR.glob("*.pdf"))[:MAX]
print(f"Found {len(pdfs)} PDFs, uploading {min(len(pdfs), MAX)} to s3://{bucket}/{S3_PREFIX}/")

samples = []
for i, pdf in enumerate(pdfs):
    # Extract name from filename like "invoice_Aaron Bergman_36258.pdf"
    stem = pdf.stem  # "invoice_Aaron Bergman_36258"
    parts = stem.split("_", 1)
    name = parts[1] if len(parts) > 1 else stem
    # Split name and number: "Aaron Bergman_36258" -> ("Aaron Bergman", "36258")
    name_match = re.match(r"(.+?)_(\d+)$", name)
    if name_match:
        vendor = name_match.group(1).strip()
        inv_num = name_match.group(2)
    else:
        vendor = name.strip()
        inv_num = hashlib.sha256(stem.encode()).hexdigest()[:8]

    # Generate realistic amount based on hash (deterministic)
    h = int(hashlib.sha256(stem.encode()).hexdigest()[:8], 16)
    amount = round(10 + (h % 99000) / 100, 2)  # $10 to $1000

    # Upload to S3
    s3_key = f"{S3_PREFIX}/{pdf.name}"
    client.put_object(
        Bucket=bucket,
        Key=s3_key,
        Body=pdf.read_bytes(),
        ContentType="application/pdf",
    )

    # Determine scenario tags
    tags = []
    if amount < 100:
        tags.append("under-100")
    elif amount > 500:
        tags.append("over-500")
    else:
        tags.append("100-500")

    # Vary scenarios deterministically
    scenario_idx = i % 5
    if scenario_idx == 0:
        confidence = "HIGH"
        po = f"PO-{inv_num}"
        label = f"Clean · {vendor}"
        expected = "Routine invoice — matched PO, approved vendor"
        tags.append("auto-clear")
    elif scenario_idx == 1:
        confidence = "HIGH"
        po = f"PO-{inv_num}"
        label = f"Over PO · {vendor}"
        expected = "Amount exceeds purchase order tolerance"
        tags.append("escalate")
        tags.append("over-po")
    elif scenario_idx == 2:
        confidence = "LOW"
        po = None
        label = f"No PO · {vendor}"
        expected = "No purchase order referenced"
        tags.append("escalate")
        tags.append("no-po")
        tags.append("low-confidence")
    elif scenario_idx == 3:
        confidence = "HIGH"
        po = f"PO-{inv_num}"
        label = f"Unknown vendor · {vendor}"
        expected = "Vendor not on approved list"
        tags.append("escalate")
        tags.append("unknown-vendor")
    else:
        confidence = "MED"
        po = f"PO-{inv_num}"
        label = f"Review · {vendor}"
        expected = "Medium confidence — needs human review"
        tags.append("escalate")
        tags.append("low-confidence")

    samples.append({
        "label": label,
        "expected": expected,
        "tags": tags,
        "vendor": vendor,
        "amount": str(amount),
        "invoice_number": f"INV-{inv_num}",
        "po_number": po,
        "confidence": confidence,
        "source_file": f"s3://{s3_key}",
    })

    print(f"  [{i+1}/{len(pdfs)}] {vendor} ${amount} → s3://{bucket}/{s3_key}")

# Write samples JSON
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(json.dumps(samples, indent=2))
print(f"\nWrote {len(samples)} samples to {OUTPUT}")
print("Done!")
