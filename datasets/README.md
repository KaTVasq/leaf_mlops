# Datasets

One directory per dataset. Only documentation, label mappings and reports are versioned;
images and generated tables are ignored by Git (licences, size).

```
datasets/<name>/
    raw/                  Original files exactly as downloaded (not versioned)
    dataset.json          Source, version, license (SPDX id), attribution, capture conditions
    label_mapping.json    Original class -> family, genus, species, with a review status
    label_ranges.csv      (Flavia only) image-number ranges -> class
    gbif_report.csv       Result of verifying the mapping against GBIF (versioned)
    interim/              Generated: images.csv (one row per image) and problems.txt
datasets/combined/        Generated: images.csv, taxonomy.csv, report.md and report.json across datasets
datasets/releases/<v>/    class_index.json (frozen class ids) and report of a final version (versioned)
datasets/_cache/          Generated: cached GBIF answers
```

## Available datasets

| Name | Where to download | Layout expected in `raw/` |
| --- | --- | --- |
| `swedish_leaf` | https://cvl.isy.liu.se/research/datasets/swedish-leaf | `leaf1/l1nr001.tif` ... (class number inside the file name) |
| `flavia` | https://flavia.sourceforge.net/ | `leaves/1001.jpg` ... (class given by `label_ranges.csv`) |

Licences are described in [../docs/dataset_survey.md](../docs/dataset_survey.md). Neither
dataset states an explicit licence: use them locally and cite the authors.

The source publishes Swedish Leaf as one archive per class (`leaf1.zip` ... `leaf15.zip`, about 3.7 GB
in total). Extract each one into `raw/leafN/`.

## Mapping status

Every entry in `label_mapping.json` has a `status`:

- `proposed_unverified`: drafted by hand or with an assistant, not checked yet.
- `verified`: GBIF returns the same accepted name and agrees on genus and family.
- `needs_review`: GBIF reports a synonym, a family disagreement or no species-level match.
  The `note` field says why. A person decides whether to edit the mapping.

## Adding a dataset

1. Create `datasets/<name>/` and write `dataset.json` (license as an SPDX id or
   `LicenseRef-...`, never free text) and `label_mapping.json` (copy the structure of an
   existing one). Genus-only classes use `"species": null`.
2. Add a reader in `src/leaf_mlops/data/readers.py` that turns the file layout into
   `ImageRecord` rows, returns the files it could not label, and has tests.
3. Run `scripts/verify_mapping.py <name>` and review everything marked `needs_review`.
4. Run `scripts/build_interim.py <name> --hash` and then `scripts/build_combined.py`.
   Taxonomy contradictions between datasets are printed as `CONFLICT` and the command
   exits with status 2.
