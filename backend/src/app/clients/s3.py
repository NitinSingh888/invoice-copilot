"""S3 client for invoice document storage.

Uploads go to: s3://{bucket}/invoices/{org_id}/{invoice_id}{ext}
Downloads use pre-signed URLs (valid 15 min, no credentials exposed).

Configured via app settings (IC_S3_BUCKET, IC_S3_REGION, etc.).
If IC_S3_BUCKET is not set, falls back to local file storage.
"""
from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

from app.core.config import get_settings

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

_client: object | None = None  # lazy singleton
_client_lock = threading.Lock()


def _bucket() -> str | None:
    b = get_settings().s3_bucket
    return b if b else None


def _get_client() -> object:
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                import boto3  # type: ignore[import-untyped]
                from botocore.config import Config  # type: ignore[import-untyped]

                settings = get_settings()
                _client = boto3.client(
                    "s3",
                    region_name=settings.s3_region,
                    aws_access_key_id=settings.s3_access_key or None,
                    aws_secret_access_key=settings.s3_secret_key or None,
                    config=Config(signature_version="s3v4"),
                )
    return _client


def is_enabled() -> bool:
    """True if S3 storage is configured."""
    return bool(_bucket())


def upload(file_bytes: bytes, key: str, content_type: str | None = None) -> str:
    """Upload bytes to S3 and return the key."""
    if content_type is None:
        import mimetypes as _mt

        content_type = _mt.guess_type(key)[0] or "application/octet-stream"
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
