"""Convert one raw dataset into the common metadata table (datasets/<name>/interim).

Usage (from the repository root):
    python scripts/build_interim.py swedish_leaf
    python scripts/build_interim.py flavia --hash --size
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from leaf_mlops.data.mapping import MappingError, build_taxonomy, load_label_mapping
from leaf_mlops.data.readers import load_flavia_ranges, read_flavia, read_swedish_leaf
from leaf_mlops.data.schema import write_records_csv


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", choices=["swedish_leaf", "flavia"])
    parser.add_argument("--datasets-dir", default="datasets", type=Path)
    parser.add_argument("--hash", action="store_true", help="compute SHA-256 of every image")
    parser.add_argument("--size", action="store_true", help="read image width and height")
    args = parser.parse_args()

    base = args.datasets_dir / args.dataset
    raw_dir = base / "raw"
    if not raw_dir.is_dir():
        print(f"ERROR: {raw_dir} does not exist. Download the dataset first.")
        return 1

    try:
        mapping = load_label_mapping(base / "label_mapping.json")
        taxonomy = build_taxonomy(mapping)
        if args.dataset == "swedish_leaf":
            records, problems = read_swedish_leaf(raw_dir, mapping, args.hash, args.size)
        else:
            ranges = load_flavia_ranges(base / "label_ranges.csv")
            records, problems = read_flavia(raw_dir, ranges, mapping, args.hash, args.size)
    except (MappingError, OSError) as error:
        print(f"ERROR: {error}")
        return 1

    out_dir = base / "interim"
    write_records_csv(records, out_dir / "images.csv")
    problems_file = out_dir / "problems.txt"
    if problems:
        problems_file.write_text("\n".join(problems) + "\n", encoding="utf-8")
    elif problems_file.exists():
        problems_file.unlink()

    per_class = Counter(record.original_label for record in records)
    print(f"{len(records)} images written to {out_dir / 'images.csv'}")
    print(f"Taxonomy: {len(taxonomy.classes('family'))} families, "
          f"{len(taxonomy.classes('genus'))} genera, {len(taxonomy.classes('species'))} species")
    for label, count in sorted(per_class.items()):
        print(f"  {label}: {count}")
    missing = [e.original for e in mapping.values() if e.original not in per_class]
    if missing:
        print(f"Classes in the mapping without images: {', '.join(missing)}")
    unverified = sum(1 for e in mapping.values() if e.status != "verified")
    if unverified:
        print(f"WARNING: {unverified} of {len(mapping)} mapping entries are not verified yet.")
    if problems:
        print(f"WARNING: {len(problems)} problems, see {problems_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
