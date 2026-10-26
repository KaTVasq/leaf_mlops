"""Taxonomic hierarchy (family > genus > species) and label encoding."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

LEVELS = ("family", "genus", "species")

# Label used when a level is unknown (e.g. a class that only reaches genus level).
# It matches the default ``ignore_index`` of torch cross-entropy losses.
IGNORE_INDEX = -1


class TaxonomyError(ValueError):
    """Raised when the taxonomy is inconsistent."""


@dataclass
class Taxonomy:
    """Maps each species to its genus and family and encodes labels as integers."""

    species_to_genus: dict[str, str] = field(default_factory=dict)
    genus_to_family: dict[str, str] = field(default_factory=dict)

    def add_genus(self, genus: str, family: str) -> None:
        """Register a genus (used for classes that do not reach species level)."""
        if self.genus_to_family.get(genus, family) != family:
            raise TaxonomyError(f"Genus '{genus}' has two different families.")
        self.genus_to_family[genus] = family

    def add(self, species: str, genus: str, family: str) -> None:
        """Register a species, rejecting contradictory parents."""
        if self.species_to_genus.get(species, genus) != genus:
            raise TaxonomyError(f"Species '{species}' has two different genera.")
        self.add_genus(genus, family)
        self.species_to_genus[species] = genus

    def classes(self, level: str) -> list[str]:
        """Sorted class names for a level (stable ordering => reproducible indices)."""
        if level == "species":
            return sorted(self.species_to_genus)
        if level == "genus":
            return sorted(self.genus_to_family)
        if level == "family":
            return sorted(set(self.genus_to_family.values()))
        raise KeyError(f"Unknown level '{level}'. Expected one of {LEVELS}.")

    def encode_label(self, genus: str, species: str | None = None) -> dict[str, int]:
        """Integer labels at every level. Unknown species gets ``IGNORE_INDEX``."""
        family = self.genus_to_family[genus]
        species_index = IGNORE_INDEX
        if species is not None:
            if self.species_to_genus.get(species) != genus:
                raise TaxonomyError(f"Species '{species}' does not belong to genus '{genus}'.")
            species_index = self.classes("species").index(species)
        return {
            "family": self.classes("family").index(family),
            "genus": self.classes("genus").index(genus),
            "species": species_index,
        }

    def encode(self, species: str) -> dict[str, int]:
        """Return the integer label of a species at every level."""
        return self.encode_label(self.species_to_genus[species], species)

    def is_consistent(self, family: str, genus: str, species: str) -> bool:
        """True if the (family, genus, species) triple respects the hierarchy."""
        return (
            self.species_to_genus.get(species) == genus
            and self.genus_to_family.get(genus) == family
        )


def load_taxonomy_from_csv(path: str | Path) -> Taxonomy:
    """Build a taxonomy from a CSV with columns: family, genus, species.

    A row with an empty species registers only the genus.
    """
    taxonomy = Taxonomy()
    with open(path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            family, genus = row["family"].strip(), row["genus"].strip()
            species = row["species"].strip()
            if species:
                taxonomy.add(species, genus, family)
            else:
                taxonomy.add_genus(genus, family)
    return taxonomy
