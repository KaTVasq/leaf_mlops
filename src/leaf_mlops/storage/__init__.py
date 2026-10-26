"""Pluggable image storage selected by configuration (see ``.env.example``)."""

from __future__ import annotations

import os
from collections.abc import Mapping

from leaf_mlops.storage.base import Storage, StorageError
from leaf_mlops.storage.local import LocalStorage
from leaf_mlops.storage.s3 import S3Storage

__all__ = ["Storage", "StorageError", "LocalStorage", "S3Storage", "get_storage"]


def get_storage(env: Mapping[str, str] | None = None) -> Storage:
    """Build the backend named by ``STORAGE_BACKEND`` (default ``local``)."""
    env = os.environ if env is None else env
    backend = env.get("STORAGE_BACKEND", "local").strip().lower()
    if backend == "local":
        return LocalStorage(env.get("MEDIA_ROOT", "./data/media"))
    if backend == "s3":
        bucket = env.get("S3_BUCKET")
        if not bucket:
            raise StorageError("STORAGE_BACKEND=s3 requires S3_BUCKET.")
        options = {
            "endpoint_url": env.get("S3_ENDPOINT_URL"),
            "aws_access_key_id": env.get("S3_ACCESS_KEY_ID"),
            "aws_secret_access_key": env.get("S3_SECRET_ACCESS_KEY"),
            "region_name": env.get("S3_REGION"),
        }
        return S3Storage(bucket, prefix=env.get("S3_PREFIX", ""), **{k: v for k, v in options.items() if v})
    raise StorageError(f"Unknown STORAGE_BACKEND '{backend}'. Use 'local' or 's3'.")
