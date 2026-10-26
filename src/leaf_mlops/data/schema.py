"""Common metadata schema: one row per image, shared by every dataset."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

FIELDS = (
    "image_id",
    "source_dataset",
    "source_image_id",
    "file_path",
    "original_label",
    "family",
    "genus",
    "species",
    "mapping_status",
    "organ",
    "capture_type",
    "background",
    "width",
    "height",
    "sha256",
    "license",
)


@dataclass
class ImageRecord:
    source_dataset: str
    source_image_id: str
    file_path: str  # relative to the dataset's raw directory, with forward slashes
    original_label: str
    family: str
    genus: str
    species: str = ""  # empty when the class only reaches genus level
    mapping_status: str = ""
    organ: str = "leaf"
    capture_type: str = ""
    background: str = ""
    width: int | None = None
    height: int | None = None
    sha256: str = ""
    license: str = ""

    @property
    def image_id(self) -> str:
        return f"{self.source_dataset}:{self.source_image_id}"

    def to_row(self) -> dict[str, str | int]:
        row = {name: getattr(self, name, "") for name in FIELDS}
        row["image_id"] = self.image_id
        return {key: ("" if value is None else value) for key, value in row.items()}


def write_records_csv(records: list[ImageRecord], path: str | Path) -> None:
    """Write records to CSV (UTF-8, header always present)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for record in records:
            writer.writerow(record.to_row())
