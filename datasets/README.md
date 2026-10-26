# Datasets

One directory per dataset. Only documentation, label mappings and reports are versioned;
images and generated tables are ignored by Git (licences, size).

```
datasets/<name>/
    raw/                  Original files exactly as downloaded (not versioned)
    label_mapping.json    Original class -> family, genus, species, with a review status
    label_ranges.csv      (Flavia only) image-number ranges -> class
    gbif_report.csv       Result of verifying the mapping against GBIF (versioned)
    interim/              Generated: images.csv (one row per image) and problems.txt
datasets/combined/        Generated: images.csv and taxonomy.csv across datasets
datasets/_cache/          Generated: cached GBIF answers
```

## Available datasets

| Name | Where to download | Layout expected in `raw/` |
| --- | --- | --- |
| `swedish_leaf` | https://cvl.isy.liu.se/research/datasets/swedish-leaf | `leaf1/l1nr001.tif` ... (class number inside the file name) |
| `flavia` | https://flavia.sourceforge.net/ | `leaves/1001.jpg` ... (class given by `label_ranges.csv`) |

Licences are described in [../docs/dataset_survey.md](../docs/dataset_survey.md). Neither
dataset states an explicit licence: use them locally and cite the authors.

## Mapping status

Every entry in `label_mapping.json` has a `status`:

- `proposed_unverified`: drafted by hand or with an assistant, not checked yet.
- `verified`: GBIF returns the same accepted name and agrees on genus and family.
- `needs_review`: GBIF reports a synonym, a family disagreement or no species-level match.
  The `note` field says why. A person decides whether to edit the mapping.

## Adding a dataset

1. Create `datasets/<name>/` and write `label_mapping.json` (copy the structure of an
   existing one). Genus-only classes use `"species": null`.
2. Add a reader in `src/leaf_mlops/data/readers.py` that turns the file layout into
   `ImageRecord` rows, returns the files it could not label, and has tests.
3. Run `scripts/verify_mapping.py <name>` and review everything marked `needs_review`.
4. Run `scripts/build_interim.py <name>` and then `scripts/build_combined.py`.
   Taxonomy contradictions between datasets are printed as `CONFLICT` and the command
   exits with status 2.
