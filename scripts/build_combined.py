"""Merge the interim tables of several datasets into datasets/combined.

Usage (from the repository root, after build_interim.py for each dataset):
    python scripts/build_combined.py swedish_leaf flavia
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from leaf_mlops.data.combine import combine, read_interim, write_combined


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("datasets", nargs="+")
    parser.add_argument("--datasets-dir", default="datasets", type=Path)
    parser.add_argument("--out", default=None, type=Path, help="default: <datasets-dir>/combined")
    args = parser.parse_args()

    tables = {}
    for name in args.datasets:
        path = args.datasets_dir / name / "interim" / "images.csv"
        if not path.is_file():
            print(f"ERROR: {path} not found. Run: python scripts/build_interim.py {name}")
            return 1
        tables[name] = read_interim(path)

    result = combine(tables)
    out_dir = args.out or args.datasets_dir / "combined"
    write_combined(result, out_dir)

    taxonomy = result.taxonomy
    print(f"{len(result.rows)} images from {len(tables)} datasets written to {out_dir}")
    print(f"Taxonomy: {len(taxonomy.classes('family'))} families, "
          f"{len(taxonomy.classes('genus'))} genera, {len(taxonomy.classes('species'))} species")
    shared = result.shared_taxa()
    print(f"Taxa present in more than one dataset: {len(shared)}")
    for name, per in shared.items():
        print(f"  {name}: " + ", ".join(f"{d}={n}" for d, n in sorted(per.items())))
    genera = result.shared_genera()
    print(f"Genera present in more than one dataset: {len(genera)}")
    for name, per in genera.items():
        print(f"  {name}: " + ", ".join(f"{d}={n}" for d, n in sorted(per.items())))
    for conflict in result.conflicts:
        print(f"CONFLICT: {conflict}")
    return 2 if result.conflicts else 0


if __name__ == "__main__":
    sys.exit(main())
