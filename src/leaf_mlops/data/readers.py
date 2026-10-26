"""Dataset readers: turn each dataset's raw layout into common ``ImageRecord`` rows.

Readers never modify or move raw files. They return the records and a list of problems
(files that could not be labelled) instead of silently dropping anything.
"""

from __future__ import annotations

import csv
import hashlib
import re
from pathlib import Path

from leaf_mlops.data.mapping import LabelEntry, MappingError
from leaf_mlops.data.schema import ImageRecord

SWEDISH_NAME = re.compile(r"^l(\d+)nr(\d+)$", re.IGNORECASE)  # e.g. l9nr003.tif
SWEDISH_SUFFIXES = {".tif", ".tiff"}
FLAVIA_SUFFIXES = {".jpg", ".jpeg"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _image_size(path: Path) -> tuple[int | None, int | None]:
    try:
        from PIL import Image

        with Image.open(path) as image:
            return image.size
    except Exception:  # unreadable or Pillow missing: leave the size empty
        return None, None


def _make_record(
    raw_dir: Path,
    path: Path,
    dataset: str,
    entry: LabelEntry,
    capture_type: str,
    background: str,
    license_note: str,
    compute_hash: bool,
    read_size: bool,
) -> ImageRecord:
    width, height = _image_size(path) if read_size else (None, None)
    return ImageRecord(
        source_dataset=dataset,
        source_image_id=path.stem.lower(),
        file_path=path.relative_to(raw_dir).as_posix(),
        original_label=entry.original,
        family=entry.family,
        genus=entry.genus,
        species=entry.species or "",
        mapping_status=entry.status,
        capture_type=capture_type,
        background=background,
        width=width,
        height=height,
        sha256=_sha256(path) if compute_hash else "",
        license=license_note,
    )


def read_swedish_leaf(
    raw_dir: str | Path,
    mapping: dict[str, LabelEntry],
    compute_hash: bool = False,
    read_size: bool = False,
) -> tuple[list[ImageRecord], list[str]]:
    """Read Swedish Leaf: the class number is part of the file name (l9nr003.tif)."""
    raw_dir = Path(raw_dir)
    found: list[tuple[int, int, Path, LabelEntry]] = []
    problems: list[str] = []

    for path in raw_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SWEDISH_SUFFIXES:
            continue
        match = SWEDISH_NAME.match(path.stem)
        if not match:
            problems.append(f"{path.relative_to(raw_dir).as_posix()}: unexpected file name")
            continue
        class_number, leaf_number = int(match.group(1)), int(match.group(2))
        entry = mapping.get(str(class_number))
        if entry is None:
            problems.append(f"{path.relative_to(raw_dir).as_posix()}: class {class_number} not in mapping")
            continue
        found.append((class_number, leaf_number, path, entry))

    found.sort(key=lambda item: (item[0], item[1]))
    records = [
        _make_record(
            raw_dir, path, "swedish_leaf", entry, "scan", "plain",
            "unspecified; cite Soderkvist 2001", compute_hash, read_size,
        )
        for _, _, path, entry in found
    ]
    return records, sorted(problems)


def load_flavia_ranges(path: str | Path) -> list[tuple[int, int, str]]:
    """Read the table that maps image numbers to class keys.

    CSV columns: first_id, last_id, key (both ends inclusive). Taken from the table on
    the Flavia web page.
    """
    ranges: list[tuple[int, int, str]] = []
    with open(path, newline="", encoding="utf-8") as handle:
        for line_number, row in enumerate(csv.DictReader(handle), start=2):
            try:
                first, last = int(row["first_id"]), int(row["last_id"])
            except (KeyError, TypeError, ValueError) as error:
                raise MappingError(f"{path}, line {line_number}: invalid first_id/last_id.") from error
            if first > last:
                raise MappingError(f"{path}, line {line_number}: first_id is greater than last_id.")
            ranges.append((first, last, (row.get("key") or "").strip()))

    ordered = sorted(ranges)
    for (_, previous_last, _), (next_first, _, _) in zip(ordered, ordered[1:], strict=False):
        if next_first <= previous_last:
            raise MappingError(f"{path}: overlapping ranges around image {next_first}.")
    return ordered


def read_flavia(
    raw_dir: str | Path,
    ranges: list[tuple[int, int, str]],
    mapping: dict[str, LabelEntry],
    compute_hash: bool = False,
    read_size: bool = False,
) -> tuple[list[ImageRecord], list[str]]:
    """Read Flavia: file names are 4-digit numbers; the range table gives the class."""
    if not ranges:
        raise MappingError("The Flavia range table is empty. Fill label_ranges.csv first.")
    raw_dir = Path(raw_dir)
    found: list[tuple[int, Path, LabelEntry]] = []
    problems: list[str] = []

    for path in raw_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in FLAVIA_SUFFIXES:
            continue
        relative = path.relative_to(raw_dir).as_posix()
        if not path.stem.isdigit():
            problems.append(f"{relative}: file name is not a number")
            continue
        number = int(path.stem)
        key = next((k for first, last, k in ranges if first <= number <= last), None)
        if key is None:
            problems.append(f"{relative}: number {number} is outside every range")
            continue
        entry = mapping.get(key)
        if entry is None:
            problems.append(f"{relative}: key '{key}' not in mapping")
            continue
        found.append((number, path, entry))

    found.sort(key=lambda item: item[0])
    records = [
        _make_record(
            raw_dir, path, "flavia", entry, "scan_or_camera", "plain",
            "unspecified; cite Wu et al. 2007", compute_hash, read_size,
        )
        for _, path, entry in found
    ]
    return records, sorted(problems)
