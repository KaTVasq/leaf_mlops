"""Merge the interim tables of several datasets into one harmonised dataset.

Usage (from the repository root, after build_interim.py for each dataset):
    python scripts/build_combined.py swedish_leaf flavia
    python scripts/build_combined.py swedish_leaf flavia --version v0.1            # freeze the class ids
    python scripts/build_combined.py swedish_leaf flavia --version v0.1 --release  # final version checks

Outputs:
    datasets/combined/            images.csv, taxonomy.csv, report.md, report.json (generated, not versioned)
    datasets/releases/<version>/  class_index.json, report.md, report.json (small, kept in Git)

The result is a derived dataset: images and labels belong to their sources and keep their licenses.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from leaf_mlops.data.class_index import ClassIndex, ClassIndexError
from leaf_mlops.data.combine import combine, read_interim, write_combined
from leaf_mlops.data.report import build_report, release_problems, write_report


def _resolve_index(args, taxonomy) -> tuple[ClassIndex | None, str | None]:
    """Load the frozen index of ``--version`` (checking the data against it) or create it."""
    if not args.version:
        return None, None
    path = args.index or args.datasets_dir / "releases" / args.version / "class_index.json"
    if path.is_file():
        index = ClassIndex.load(path)
        if index.version != args.version:
            raise ClassIndexError(f"{path} is version '{index.version}', not '{args.version}'.")
        missing = index.missing_from(taxonomy)
        if missing:
            raise ClassIndexError(
                f"{len(missing)} classes are not in the frozen index {path} (for example {missing[0]}). "
                "A frozen version cannot change: use a new --version."
            )
        return index, f"checked against frozen index {path}"
    index = ClassIndex.from_taxonomy(taxonomy, args.version)
    index.save(path)
    return index, f"created frozen index {path}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("datasets", nargs="+")
    parser.add_argument("--datasets-dir", default="datasets", type=Path)
    parser.add_argument("--out", default=None, type=Path, help="default: <datasets-dir>/combined")
    parser.add_argument("--version", default="", help="dataset version; creates or checks its frozen class index")
    parser.add_argument("--index", default=None, type=Path, help="class index file (default: releases/<version>)")
    parser.add_argument("--release", action="store_true",
                        help="require what a final version needs (frozen index, hashes, verified labels); "
                             "exit 3 if anything is missing")
    args = parser.parse_args()

    if args.release and not args.version:
        print("ERROR: --release needs --version.")
        return 1

    tables = {}
    for name in args.datasets:
        path = args.datasets_dir / name / "interim" / "images.csv"
        if not path.is_file():
            print(f"ERROR: {path} not found. Run: python scripts/build_interim.py {name}")
            return 1
        tables[name] = read_interim(path)

    result = combine(tables)
    try:
        index, index_message = _resolve_index(args, result.taxonomy)
    except (ClassIndexError, OSError) as error:
        print(f"ERROR: {error}")
        return 1

    out_dir = args.out or args.datasets_dir / "combined"
    write_combined(result, out_dir, index)
    report = build_report(result, index)
    write_report(report, out_dir)
    if args.version:
        write_report(report, args.datasets_dir / "releases" / args.version)

    taxonomy = result.taxonomy
    print(f"{len(result.rows)} images from {len(tables)} datasets written to {out_dir}")
    print(f"Taxonomy: {len(taxonomy.classes('family'))} families, "
          f"{len(taxonomy.classes('genus'))} genera, {len(taxonomy.classes('species'))} species")
    if index_message:
        print(f"Class index: {index_message} (fingerprint {index.fingerprint[:12]})")
    shared = result.shared_taxa()
    print(f"Taxa present in more than one dataset: {len(shared)}")
    for name, per in shared.items():
        print(f"  {name}: " + ", ".join(f"{d}={n}" for d, n in sorted(per.items())))
    genera = result.shared_genera()
    print(f"Genera present in more than one dataset: {len(genera)}")
    for name, per in genera.items():
        print(f"  {name}: " + ", ".join(f"{d}={n}" for d, n in sorted(per.items())))
    print(f"Report: {out_dir / 'report.md'}")
    for conflict in result.conflicts:
        print(f"CONFLICT: {conflict}")

    if args.release:
        problems = release_problems(result, index)
        for problem in problems:
            print(f"NOT RELEASABLE: {problem}")
        if problems:
            return 3
        print(f"Release checks passed for version {args.version}.")
    return 2 if result.conflicts else 0


if __name__ == "__main__":
    sys.exit(main())
