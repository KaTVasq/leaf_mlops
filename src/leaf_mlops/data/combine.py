"""Merge per-dataset metadata tables into one table with a single taxonomy.

Each dataset first gets its own ``interim/images.csv`` (see ``scripts/build_interim.py``).
Combining them is where label unification pays off: the same species must carry the same
genus and family everywhere, and species found in several datasets become the pairs that
domain-shift experiments need.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from leaf_mlops.data.names import normalize_key
from leaf_mlops.data.schema import FIELDS
from leaf_mlops.data.taxonomy import Taxonomy, TaxonomyError


@dataclass
class CombinedDataset:
    rows: list[dict[str, str]]
    taxonomy: Taxonomy
    conflicts: list[str] = field(default_factory=list)
    # taxon name -> dataset -> number of images (species, or genus for genus-only classes)
    counts: dict[str, dict[str, int]] = field(default_factory=dict)
    # genus -> dataset -> number of images (every image, whatever its species)
    genus_counts: dict[str, dict[str, int]] = field(default_factory=dict)

    def shared_genera(self) -> dict[str, dict[str, int]]:
        """Genera that appear in two or more datasets (usable even for genus-only classes)."""
        return {name: per for name, per in sorted(self.genus_counts.items()) if len(per) > 1}

    def shared_taxa(self) -> dict[str, dict[str, int]]:
        """Taxa that appear in two or more datasets."""
        return {name: per for name, per in sorted(self.counts.items()) if len(per) > 1}


def read_interim(path: str | Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def combine(tables: dict[str, list[dict[str, str]]]) -> CombinedDataset:
    """Merge rows of several datasets, collecting every taxonomic contradiction."""
    taxonomy = Taxonomy()
    conflicts: list[str] = []
    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    genus_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    spellings: dict[str, set[str]] = defaultdict(set)
    rows: list[dict[str, str]] = []
    seen_ids: dict[str, str] = {}

    for dataset in sorted(tables):
        for row in tables[dataset]:
            image_id = row["image_id"]
            if image_id in seen_ids:
                conflicts.append(f"duplicate image_id '{image_id}' in {dataset} and {seen_ids[image_id]}")
                continue
            seen_ids[image_id] = dataset

            species, genus, family = row["species"], row["genus"], row["family"]
            try:
                if species:
                    taxonomy.add(species, genus, family)
                else:
                    taxonomy.add_genus(genus, family)
            except TaxonomyError as error:
                conflicts.append(f"{image_id}: {error}")
                continue
            name = species or genus
            counts[name][dataset] += 1
            genus_counts[genus][dataset] += 1
            spellings[normalize_key(name)].add(name)
            rows.append({field_name: row.get(field_name, "") for field_name in FIELDS})

    for variants in spellings.values():
        if len(variants) > 1:
            conflicts.append(f"same taxon written differently: {sorted(variants)}")

    return CombinedDataset(
        rows, taxonomy, conflicts,
        {k: dict(v) for k, v in counts.items()},
        {k: dict(v) for k, v in genus_counts.items()},
    )


def write_combined(result: CombinedDataset, out_dir: str | Path) -> None:
    """Write ``images.csv`` and ``taxonomy.csv`` (one row per species or genus-only class)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(out_dir / "images.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(result.rows)

    datasets = sorted({d for per in result.counts.values() for d in per})
    taxonomy = result.taxonomy
    with open(out_dir / "taxonomy.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["family", "genus", "species", *[f"n_{d}" for d in datasets]])
        entries = [(taxonomy.genus_to_family[g], g, s) for s, g in taxonomy.species_to_genus.items()]
        # genus-only classes, even when the genus also has species in another dataset
        genus_only = [g for g in result.counts if g in taxonomy.genus_to_family and g not in taxonomy.species_to_genus]
        entries += [(taxonomy.genus_to_family[g], g, "") for g in genus_only]
        for family, genus, species in sorted(entries):
            per = result.counts.get(species or genus, {})
            writer.writerow([family, genus, species, *[per.get(d, 0) for d in datasets]])
