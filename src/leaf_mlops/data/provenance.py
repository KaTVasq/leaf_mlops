"""Structured provenance and license of a source dataset (``datasets/<name>/dataset.json``).

Licenses are stored as machine-readable values (an SPDX identifier or a ``LicenseRef-`` custom
identifier) instead of free text, so images can be filtered and validated automatically.
Free-text explanations go in ``license_note`` and are never used for filtering.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

# SPDX identifiers that datasets in this project are likely to use. Extend when a new one appears.
SPDX_LICENSES = frozenset({
    "CC0-1.0",
    "CC-BY-3.0",
    "CC-BY-4.0",
    "CC-BY-SA-4.0",
    "CC-BY-NC-4.0",
    "CC-BY-NC-SA-4.0",
})
UNSPECIFIED_LICENSE = "LicenseRef-unspecified"
REDISTRIBUTION_VALUES = ("allowed", "not_allowed", "unknown")

_LICENSE_REF = re.compile(r"^LicenseRef-[A-Za-z0-9.\-]+$")
_REQUIRED = ("name", "source_version", "source_url", "license_id", "redistribution",
             "attribution", "capture_type", "background")


class ProvenanceError(ValueError):
    """Raised when a dataset information file is invalid."""


@dataclass(frozen=True)
class DatasetInfo:
    name: str
    source_version: str  # release of the source ("2015", "v2"), or "unversioned"
    source_url: str
    license_id: str
    redistribution: str  # allowed | not_allowed | unknown
    attribution: str  # credit or citation that users of the data must give
    capture_type: str
    background: str
    license_note: str = ""


def is_valid_license_id(value: str) -> bool:
    return value in SPDX_LICENSES or bool(_LICENSE_REF.match(value))


def commercial_use_allowed(license_id: str) -> bool:
    """False for non-commercial and for unspecified licenses (nothing grants the right)."""
    return license_id in SPDX_LICENSES and "-NC-" not in license_id


def provenance_problems(license_id: str, redistribution: str, attribution: str, source_url: str) -> list[str]:
    """Problems with the structured provenance of one dataset or one image (empty list = valid)."""
    problems: list[str] = []
    if not license_id:
        problems.append("license_id is empty")
    elif not is_valid_license_id(license_id):
        problems.append(f"license_id '{license_id}' is neither an accepted SPDX id nor LicenseRef-...")
    if redistribution not in REDISTRIBUTION_VALUES:
        problems.append(f"redistribution '{redistribution}' is not one of {REDISTRIBUTION_VALUES}")
    if license_id == UNSPECIFIED_LICENSE and redistribution == "allowed":
        problems.append("redistribution cannot be 'allowed' when the license is unspecified")
    if license_id != "CC0-1.0" and not attribution.strip():
        problems.append("attribution is empty")
    if source_url and not source_url.startswith(("http://", "https://")):
        problems.append(f"source_url '{source_url}' is not an http(s) URL")
    return problems


def load_dataset_info(path: str | Path) -> DatasetInfo:
    """Read and validate a ``dataset.json`` file."""
    path = Path(path)
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    missing = [name for name in _REQUIRED if not str(data.get(name) or "").strip()]
    if missing:
        raise ProvenanceError(f"{path}: missing or empty fields: {', '.join(missing)}")
    if data["name"] != path.parent.name:
        raise ProvenanceError(f"{path}: name '{data['name']}' does not match folder '{path.parent.name}'")
    problems = provenance_problems(
        data["license_id"], data["redistribution"], data["attribution"], data["source_url"]
    )
    if problems:
        raise ProvenanceError(f"{path}: " + "; ".join(problems))
    return DatasetInfo(
        name=data["name"],
        source_version=str(data["source_version"]),
        source_url=data["source_url"],
        license_id=data["license_id"],
        redistribution=data["redistribution"],
        attribution=data["attribution"].strip(),
        capture_type=data["capture_type"],
        background=data["background"],
        license_note=data.get("license_note", ""),
    )
