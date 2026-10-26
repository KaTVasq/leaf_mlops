"""Label mappings: dataset-specific class keys -> unified taxonomy.

A mapping file is a reviewable JSON document kept in Git next to the dataset
documentation. Every entry carries a status so unverified labels are never mistaken
for verified ones.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from leaf_mlops.data.taxonomy import Taxonomy

STATUSES = ("verified", "proposed_unverified", "needs_review")


class MappingError(ValueError):
    """Raised when a mapping file or a range table is invalid."""


@dataclass(frozen=True)
class LabelEntry:
    key: str
    original: str
    family: str
    genus: str
    species: str | None
    status: str
    variant: str | None = None
    note: str = ""


def load_label_mapping(path: str | Path) -> dict[str, LabelEntry]:
    """Read a mapping JSON file and validate every entry."""
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    classes = data.get("classes")
    if not isinstance(classes, dict):
        raise MappingError(f"{path}: missing 'classes' object.")

    entries: dict[str, LabelEntry] = {}
    for key, raw in classes.items():
        for required in ("original", "family", "genus", "status"):
            if not str(raw.get(required) or "").strip():
                raise MappingError(f"{path}: class '{key}' needs a non-empty '{required}'.")
        if raw["status"] not in STATUSES:
            raise MappingError(f"{path}: class '{key}' has unknown status '{raw['status']}'.")
        species = (raw.get("species") or "").strip() or None
        if species and not species.startswith(f"{raw['genus']} "):
            raise MappingError(f"{path}: class '{key}': species '{species}' is not in genus '{raw['genus']}'.")
        entries[str(key)] = LabelEntry(
            key=str(key),
            original=raw["original"].strip(),
            family=raw["family"].strip(),
            genus=raw["genus"].strip(),
            species=species,
            status=raw["status"],
            variant=(raw.get("variant") or "").strip() or None,
            note=raw.get("note", ""),
        )
    return entries


def build_taxonomy(entries: dict[str, LabelEntry]) -> Taxonomy:
    """Build a taxonomy from mapping entries (raises on contradictions)."""
    taxonomy = Taxonomy()
    for entry in entries.values():
        if entry.species:
            taxonomy.add(entry.species, entry.genus, entry.family)
        else:
            taxonomy.add_genus(entry.genus, entry.family)
    return taxonomy
