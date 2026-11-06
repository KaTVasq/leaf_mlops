"""Frozen class index: the fixed link between each taxonomic class and its integer id.

``Taxonomy.encode`` numbers classes by their position in an alphabetically sorted list, so
adding one class shifts the ids of the others and silently breaks any trained model. A
``ClassIndex`` is written once per dataset version, kept in Git, and every later build is
checked against it. A change of classes means a new version, never an edit.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from leaf_mlops.data.taxonomy import IGNORE_INDEX, LEVELS, Taxonomy

FORMAT_VERSION = 1


class ClassIndexError(ValueError):
    """Raised when an index file is invalid, was edited or does not match the data."""


@dataclass(frozen=True)
class ClassIndex:
    version: str
    levels: dict[str, tuple[str, ...]]  # level -> class names; the id of a class is its position

    @classmethod
    def from_taxonomy(cls, taxonomy: Taxonomy, version: str) -> ClassIndex:
        if not version.strip():
            raise ClassIndexError("A class index needs a non-empty version.")
        return cls(version, {level: tuple(taxonomy.classes(level)) for level in LEVELS})

    @property
    def fingerprint(self) -> str:
        """SHA-256 of the class lists: record it with a model to know which ids it was trained with."""
        canonical = json.dumps({level: list(names) for level, names in sorted(self.levels.items())},
                               ensure_ascii=False, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def id_of(self, level: str, name: str) -> int:
        try:
            return self.levels[level].index(name)
        except (KeyError, ValueError):
            raise ClassIndexError(f"{level} '{name}' is not in class index {self.version}.") from None

    def encode(self, family: str, genus: str, species: str = "") -> dict[str, int]:
        """Integer labels of one sample. An empty species gets ``IGNORE_INDEX``."""
        return {
            "family": self.id_of("family", family),
            "genus": self.id_of("genus", genus),
            "species": self.id_of("species", species) if species else IGNORE_INDEX,
        }

    def missing_from(self, taxonomy: Taxonomy) -> list[str]:
        """Classes present in the data but absent from this index (must be empty to use it)."""
        known = {level: set(names) for level, names in self.levels.items()}
        return [f"{level} '{name}'" for level in LEVELS for name in taxonomy.classes(level)
                if name not in known[level]]

    def unused_in(self, taxonomy: Taxonomy) -> list[str]:
        """Classes in the index without data in this build (allowed: their ids stay reserved)."""
        present = {level: set(taxonomy.classes(level)) for level in LEVELS}
        return [f"{level} '{name}'" for level in LEVELS for name in self.levels[level]
                if name not in present[level]]

    def to_dict(self) -> dict:
        return {
            "format": FORMAT_VERSION,
            "version": self.version,
            "ignore_index": IGNORE_INDEX,
            "fingerprint": self.fingerprint,
            "levels": {level: {name: i for i, name in enumerate(names)} for level, names in self.levels.items()},
        }

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> ClassIndex:
        """Read an index file, checking its ids and its fingerprint (detects manual edits)."""
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        if data.get("format") != FORMAT_VERSION:
            raise ClassIndexError(f"{path}: unsupported format {data.get('format')!r}.")
        levels: dict[str, tuple[str, ...]] = {}
        for level in LEVELS:
            mapping = data.get("levels", {}).get(level)
            if not isinstance(mapping, dict):
                raise ClassIndexError(f"{path}: missing level '{level}'.")
            if sorted(mapping.values()) != list(range(len(mapping))):
                raise ClassIndexError(f"{path}: ids of '{level}' are not 0..{len(mapping) - 1} without gaps.")
            levels[level] = tuple(sorted(mapping, key=mapping.__getitem__))
        index = cls(str(data.get("version", "")), levels)
        if index.fingerprint != data.get("fingerprint"):
            raise ClassIndexError(f"{path}: fingerprint mismatch; a frozen index must not be edited.")
        return index
