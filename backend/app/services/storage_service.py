"""Unified file storage abstraction — local filesystem or S3/MinIO.

Usage:
    from app.services.storage_service import storage

    url = await storage.save(content_bytes, "medical_images/abc.jpg", "image/jpeg")
    await storage.delete("medical_images/abc.jpg")

Configuration (app/core/config.py):
    USE_S3=false  → saves to MEDIA_ROOT on local disk, served via FastAPI StaticFiles
    USE_S3=true   → uploads to S3/MinIO bucket, returns CDN or presigned URL
"""
from __future__ import annotations

import io
import os
from pathlib import Path
from typing import Optional

import aiofiles

from app.core.config import settings


class LocalStorage:
    """Saves files to MEDIA_ROOT and returns MEDIA_URL-based public URLs."""

    def __init__(self) -> None:
        self.root = Path(settings.MEDIA_ROOT)

    async def save(self, content: bytes, relative_path: str, content_type: str = "") -> str:
        dest = self.root / relative_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(dest, "wb") as f:
            await f.write(content)
        # Return public URL
        return f"{settings.MEDIA_URL}/{relative_path}"

    async def delete(self, relative_path: str) -> None:
        dest = self.root / relative_path
        try:
            dest.unlink(missing_ok=True)
        except OSError:
            pass

    def public_url(self, relative_path: str) -> str:
        return f"{settings.MEDIA_URL}/{relative_path}"


class S3Storage:
    """Uploads files to S3/MinIO and returns CDN or presigned public URLs."""

    def __init__(self) -> None:
        try:
            import boto3
            self._s3 = boto3.client(
                "s3",
                region_name=settings.AWS_S3_REGION_NAME,
                endpoint_url=settings.AWS_S3_ENDPOINT_URL or None,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            )
        except ImportError:
            raise RuntimeError(
                "boto3 is required for S3 storage. Install it: pip install boto3"
            )

    async def save(self, content: bytes, relative_path: str, content_type: str = "") -> str:
        import asyncio

        bucket = settings.AWS_STORAGE_BUCKET_NAME
        # Run blocking S3 upload in threadpool so we don't block the event loop
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self._s3.put_object(
                Bucket=bucket,
                Key=relative_path,
                Body=content,
                ContentType=content_type or "application/octet-stream",
                ACL="public-read",
            ),
        )
        return self.public_url(relative_path)

    async def delete(self, relative_path: str) -> None:
        import asyncio

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self._s3.delete_object(
                Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=relative_path
            ),
        )

    def public_url(self, relative_path: str) -> str:
        if settings.AWS_S3_CUSTOM_DOMAIN:
            return f"https://{settings.AWS_S3_CUSTOM_DOMAIN}/{relative_path}"
        endpoint = settings.AWS_S3_ENDPOINT_URL or f"https://s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com"
        return f"{endpoint}/{settings.AWS_STORAGE_BUCKET_NAME}/{relative_path}"


# Singleton — selected at import time based on config
storage: LocalStorage | S3Storage = (
    S3Storage() if settings.USE_S3 else LocalStorage()
)
