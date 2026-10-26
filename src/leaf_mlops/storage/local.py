"""Local file system backend (default for development: no account or credentials needed)."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import BinaryIO

from leaf_mlops.storage.base import Storage, StorageError, validate_key


class LocalStorage(Storage):
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        path = (self.root / validate_key(key)).resolve()
        if self.root not in path.parents:
            raise StorageError(f"Key escapes the storage root: {key!r}")
        return path

    def save(self, key: str, data: bytes | BinaryIO) -> str:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + ".part")  # write then rename: no half-written files
        with open(temporary, "wb") as handle:
            if isinstance(data, (bytes, bytearray)):
                handle.write(data)
            else:
                shutil.copyfileobj(data, handle)
        temporary.replace(path)
        return key

    def open(self, key: str) -> BinaryIO:
        path = self._path(key)
        if not path.is_file():
            raise StorageError(f"Object not found: {key}")
        return open(path, "rb")

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)

    def list_keys(self, prefix: str = "") -> list[str]:
        keys = (p.relative_to(self.root).as_posix() for p in self.root.rglob("*") if p.is_file())
        return sorted(k for k in keys if k.startswith(prefix) and not k.endswith(".part"))
