"""Storage interface: the application only talks to this, never to a concrete backend."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import BinaryIO


class StorageError(RuntimeError):
    """Raised for invalid keys, missing objects or backend failures."""


class Storage(ABC):
    """Minimal object store. Keys are relative POSIX paths such as ``flavia/1001.jpg``."""

    @abstractmethod
    def save(self, key: str, data: bytes | BinaryIO) -> str:
        """Store ``data`` under ``key`` (overwriting) and return the key."""

    @abstractmethod
    def open(self, key: str) -> BinaryIO:
        """Open an object for reading. Raises ``StorageError`` if it does not exist."""

    @abstractmethod
    def exists(self, key: str) -> bool: ...

    @abstractmethod
    def delete(self, key: str) -> None:
        """Remove an object. Deleting a missing key is not an error."""

    @abstractmethod
    def list_keys(self, prefix: str = "") -> list[str]:
        """Sorted keys that start with ``prefix``."""


def validate_key(key: str) -> str:
    """Reject keys that could escape the storage root or are ambiguous."""
    parts = key.split("/")
    if not key or key.startswith("/") or "\\" in key or "\x00" in key or any(p in ("", ".", "..") for p in parts):
        raise StorageError(f"Invalid storage key: {key!r}")
    return key
