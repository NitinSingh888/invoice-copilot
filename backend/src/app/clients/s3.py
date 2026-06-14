"""S3 client for invoice document storage.

Uploads go to: s3://{bucket}/invoices/{org_id}/{invoice_id}{ext}
Downloads use pre-signed URLs (valid 15 min, no credentials exposed).

Configured via environment variables:
  IC_S3_BUCKET, IC_S3_REGION, IC_S3_ACCESS_KEY, IC_S3_SECRET_KEY
If IC_S3_BUCKET is not set, falls back to local file storage.
"""
from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

_client: object | None = None  # lazy singleton


def _bucket() -> str | None:
    return os.environ.get("IC_S3_BUCKET")


def _get_client() -> object:
    global _client
    if _client is None:
        import boto3  # type: ignore[import-untyped]

        _client = boto3.client(
            "s3",
            region_name=os.environ.get("IC_S3_REGION", "us-east-1"),
            aws_access_key_id=os.environ.get("IC_S3_ACCESS_KEY"),
            aws_secret_access_key=os.environ.get("IC_S3_SECRET_KEY"),
        )
    return _client


def is_enabled() -> bool:
    """True if S3 storage is configured."""
    return bool(_bucket())


def upload(file_bytes: bytes, key: str, content_type: str = "application/pdf") -> str:
    """Upload bytes to S3 and return the key."""
    bucket = _bucket()
    if not bucket:
        raise RuntimeError("S3 not configured (IC_S3_BUCKET not set)")
    client: object = _get_client()
    client.put_object(  # type: ignore[attr-defined]
        Bucket=bucket,
        Key=key,
        Body=file_bytes,
        ContentType=content_type,
    )
    logger.info("Uploaded %d bytes to s3://%s/%s", len(file_bytes), bucket, key)
    return key


def presigned_url(key: str, expires_in: int = 900) -> str:
    """Generate a pre-signed GET URL (default 15 min)."""
    bucket = _bucket()
    if not bucket:
        raise RuntimeError("S3 not configured")
    client: object = _get_client()
    url: str = client.generate_presigned_url(  # type: ignore[attr-defined]
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expires_in,
    )
    return url


def make_key(org_id: str, invoice_id: str, ext: str) -> str:
    """Build the S3 object key for an invoice document."""
    return f"invoices/{org_id}/{invoice_id}{ext}"
