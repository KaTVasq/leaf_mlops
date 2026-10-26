"""Check a dataset's label mapping against the GBIF Backbone Taxonomy.

Usage (from the repository root):
    python scripts/verify_mapping.py swedish_leaf            # report only
    python scripts/verify_mapping.py flavia --apply          # also update status/note in the JSON

The report is written to datasets/<name>/gbif_report.csv. Family, genus and species are
never changed automatically: review the report and edit the mapping by hand.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

from leaf_mlops.data.gbif import CachedMatcher, GbifError, apply_verdicts, verify_mapping
from leaf_mlops.data.mapping import MappingError, load_label_mapping


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset")
    parser.add_argument("--datasets-dir", default="datasets", type=Path)
    parser.add_argument("--cache", default="datasets/_cache/gbif.json", type=Path)
    parser.add_argument("--apply", action="store_true", help="write status and notes into the mapping JSON")
    args = parser.parse_args()

    mapping_path = args.datasets_dir / args.dataset / "label_mapping.json"
    try:
        entries = load_label_mapping(mapping_path)
        matcher = CachedMatcher(cache_path=args.cache, delay=0.1)
        verdicts = verify_mapping(entries, matcher)
    except (MappingError, GbifError, OSError) as error:
        print(f"ERROR: {error}")
        return 1
    matcher.save()

    report = args.datasets_dir / args.dataset / "gbif_report.csv"
    with open(report, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["key", "original", "status", "gbif_name", "gbif_status", "gbif_family", "findings"])
        for verdict in verdicts:
            entry = entries[verdict.key]
            m = verdict.match
            writer.writerow([verdict.key, entry.original, verdict.status, m.canonical_name,
                             m.status, m.family, verdict.message])

    counts = Counter(v.status for v in verdicts)
    print(f"{args.dataset}: {counts['verified']} verified, {counts['needs_review']} need review")
    for verdict in verdicts:
        if verdict.status != "verified":
            print(f"  [{verdict.key}] {entries[verdict.key].original}: {verdict.message}")
    print(f"Report: {report}")

    if args.apply:
        changed = apply_verdicts(mapping_path, verdicts)
        print(f"Mapping updated ({changed} entries changed).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
