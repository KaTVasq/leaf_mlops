"""Re-hash the raw images listed in a table and compare with the recorded SHA-256.

Usage (from the repository root):
    python scripts/verify_integrity.py datasets/combined/images.csv

Exit code 0 when every file matches, 2 when a file changed or is missing, 1 on a usage error.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from leaf_mlops.data.combine import read_interim
from leaf_mlops.data.integrity import verify_hashes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("table", type=Path, help="images.csv of a dataset or of the combined dataset")
    parser.add_argument("--datasets-dir", default="datasets", type=Path)
    args = parser.parse_args()

    if not args.table.is_file():
        print(f"ERROR: {args.table} not found.")
        return 1
    result = verify_hashes(read_interim(args.table), args.datasets_dir)

    print(f"ok: {len(result['ok'])}, changed: {len(result['changed'])}, "
          f"missing: {len(result['missing'])}, without recorded hash: {len(result['no_hash'])}")
    for label in ("changed", "missing"):
        for image_id in result[label][:10]:
            print(f"  {label}: {image_id}")
        if len(result[label]) > 10:
            print(f"  ... and {len(result[label]) - 10} more {label}")
    if result["no_hash"]:
        print("Rows without a hash cannot be checked: rebuild with build_interim.py --hash.")
    return 2 if result["changed"] or result["missing"] else 0


if __name__ == "__main__":
    sys.exit(main())
