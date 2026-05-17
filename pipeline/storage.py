from __future__ import annotations

import mimetypes
from pathlib import Path

import boto3
from botocore.config import Config

from pipeline import config
from pipeline.utils import get_logger

logger = get_logger(__name__)

_CONTENT_TYPES: dict[str, str] = {
    ".mp3":  "audio/mpeg",
    ".wav":  "audio/wav",
    ".png":  "image/png",
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".json": "application/json",
}


def _get_client():
    if not config.R2_ACCOUNT_ID or not config.R2_ACCESS_KEY_ID:
        raise RuntimeError("R2 credentials not configured (R2_ACCOUNT_ID / R2_ACCESS_KEY_ID)")
    return boto3.client(
        "s3",
        endpoint_url=f"https://{config.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=config.R2_ACCESS_KEY_ID,
        aws_secret_access_key=config.R2_SECRET_ACCESS_KEY,
        region_name="auto",
        config=Config(signature_version="s3v4"),
    )


def is_configured() -> bool:
    return bool(config.R2_ACCOUNT_ID and config.R2_ACCESS_KEY_ID and config.R2_BUCKET_NAME)


def upload_file(local_path: Path, key: str) -> str:
    """Upload a local file to R2 and return its public CDN URL."""
    ext = local_path.suffix.lower()
    content_type = _CONTENT_TYPES.get(ext) or mimetypes.guess_type(str(local_path))[0] or "application/octet-stream"

    client = _get_client()
    client.upload_file(
        str(local_path),
        config.R2_BUCKET_NAME,
        key,
        ExtraArgs={
            "ContentType": content_type,
            "CacheControl": "public, max-age=86400",
        },
    )
    url = f"{config.R2_PUBLIC_URL.rstrip('/')}/{key}"
    logger.info(f"[storage] Uploaded {local_path.name} → {url}")
    return url


def upload_bytes(data: bytes, key: str, content_type: str) -> str:
    """Upload raw bytes to R2 and return its public CDN URL."""
    client = _get_client()
    client.put_object(
        Bucket=config.R2_BUCKET_NAME,
        Key=key,
        Body=data,
        ContentType=content_type,
        CacheControl="public, max-age=30",
    )
    url = f"{config.R2_PUBLIC_URL.rstrip('/')}/{key}"
    logger.info(f"[storage] Uploaded bytes → {url}")
    return url
