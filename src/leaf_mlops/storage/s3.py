"""S3-compatible backend: works with MinIO, Cloudflare R2, AWS S3, etc.

Requires the optional dependency ``boto3`` (``pip install -e ".[s3]"``). The client can be
injected, which is how the tests run without any network or account.
"""

from __future__ import annotations

import io
from typing import Any, BinaryIO

from leaf_mlops.storage.base import Storage, StorageError, validate_key


class S3Storage(Storage):
    def __init__(self, bucket: str, client: Any = None, prefix: str = "", **client_options: Any):
        if client is None:
            try:
                import boto3
            except ImportError as error:
                raise StorageError('boto3 is required for the s3 backend: pip install -e ".[s3]"') from error
            client = boto3.client("s3", **client_options)
        self.bucket = bucket
        self.prefix = prefix.strip("/") + "/" if prefix.strip("/") else ""
        self._client = client

    def _key(self, key: str) -> str:
        return self.prefix + validate_key(key)

    def save(self, key: str, data: bytes | BinaryIO) -> str:
        body = bytes(data) if isinstance(data, (bytes, bytearray)) else data.read()
        self._client.put_object(Bucket=self.bucket, Key=self._key(key), Body=body)
        return key

    def open(self, key: str) -> BinaryIO:
        try:
            response = self._client.get_object(Bucket=self.bucket, Key=self._key(key))
        except Exception as error:  # botocore ClientError (NoSuchKey) without importing botocore
            raise StorageError(f"Object not found: {key}") from error
        return io.BytesIO(response["Body"].read())

    def exists(self, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self.bucket, Key=self._key(key))
            return True
        except Exception:
            return False

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self.bucket, Key=self._key(key))

    def list_keys(self, prefix: str = "") -> list[str]:
        keys: list[str] = []
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=self.prefix + prefix):
            keys.extend(item["Key"][len(self.prefix):] for item in page.get("Contents", []))
        return sorted(keys)
