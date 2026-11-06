"""File integrity: SHA-256 of images and re-checking them against a metadata table.

A hash in the metadata table ties a row to the exact bytes it was built from. Final dataset
versions must carry it (see ``release_problems`` in ``leaf_mlops.data.report``).
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from pathlib import Path


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_hashes(rows: Iterable[dict[str, str]], datasets_dir: str | Path) -> dict[str, list[str]]:
    """Re-hash the raw files of ``rows`` and compare with their ``sha256`` column.

    Returns the ``image_id`` of every row in each category: ``ok``, ``changed`` (file differs from
    the recorded hash), ``missing`` (file not found) and ``no_hash`` (row has no recorded hash).
    """
    result: dict[str, list[str]] = {"ok": [], "changed": [], "missing": [], "no_hash": []}
    for row in rows:
        image_id = row["image_id"]
        if not row.get("sha256"):
            result["no_hash"].append(image_id)
            continue
        path = Path(datasets_dir) / row["source_dataset"] / "raw" / row["file_path"]
        if not path.is_file():
            result["missing"].append(image_id)
        elif sha256_file(path) != row["sha256"]:
            result["changed"].append(image_id)
        else:
            result["ok"].append(image_id)
    return result
