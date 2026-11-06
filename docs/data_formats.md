# Data formats

Definition of every file the project reads or writes: what each column or field means, which
values it can take and how it is produced. It is the reference for people who use the
exported tables (the other TFGs and external researchers) and the source for the
corresponding chapter of the thesis.

- **Last updated:** 06/11/2026
- **Encoding:** all text files are UTF-8, with `\n` or `\r\n` line ends. CSV files always have a header row.
- **Missing values:** an empty cell means "not available" (never `NA` or `null` in CSV).
- **Example values** come from the Swedish Leaf and Flavia datasets.
- **Terminology:** the output of `build_combined.py` is a *harmonised dataset derived from* its
  sources, not a new dataset. The images, and the original labels, belong to the sources and keep
  their licenses; what this project adds is a unified taxonomy, structured metadata and checks.

## 1. Overview

| File | Location | Produced by | Versioned in Git | Section |
| --- | --- | --- | --- | --- |
| `label_mapping.json` | `datasets/<name>/` | By hand, then `verify_mapping.py --apply` | Yes | [2](#2-label_mappingjson) |
| `label_ranges.csv` | `datasets/flavia/` | By hand | Yes | [3](#3-label_rangescsv) |
| `dataset.json` | `datasets/<name>/` | By hand | Yes | [10](#10-datasetjson) |
| `images.csv` (per dataset) | `datasets/<name>/interim/` | `build_interim.py` | No (generated) | [4](#4-imagescsv) |
| `problems.txt` | `datasets/<name>/interim/` | `build_interim.py` | No (generated) | [5](#5-problemstxt) |
| `gbif_report.csv` | `datasets/<name>/` | `verify_mapping.py` | Yes | [6](#6-gbif_reportcsv) |
| `images.csv` (combined) | `datasets/combined/` | `build_combined.py` | No (generated) | [7](#7-combined-imagescsv) |
| `taxonomy.csv` | `datasets/combined/` | `build_combined.py` | No (generated) | [8](#8-taxonomycsv) |
| `class_index.json` | `datasets/releases/<version>/` | `build_combined.py --version` | Yes (once final) | [11](#11-class_indexjson) |
| `report.md`, `report.json` | `datasets/combined/` and `datasets/releases/<version>/` | `build_combined.py` | Release copy only | [12](#12-reportmd-and-reportjson) |

Data flow:

```text
raw images + dataset.json + label_mapping.json (+ label_ranges.csv)
        │  build_interim.py [--hash]
        ▼
datasets/<name>/interim/images.csv ──► build_combined.py ──► datasets/combined/images.csv
                                         [--version V]   ├─► datasets/combined/taxonomy.csv
                                         [--release]     ├─► report.md, report.json
                                                         └─► datasets/releases/V/class_index.json
label_mapping.json ──► verify_mapping.py ──► gbif_report.csv
datasets/combined/images.csv ──► verify_integrity.py (re-hashes the raw files)
```

## 2. `label_mapping.json`

Translates the classes of one dataset (as the authors named them) into the unified
taxonomy. It is a reviewable document kept in Git.

Top-level fields:

| Field | Type | Meaning |
| --- | --- | --- |
| `dataset` | text | Dataset name, equal to the folder name. |
| `taxonomy_source` | text | How the taxonomy was obtained and whether it was checked. Updated by `verify_mapping.py --apply`. |
| `classes` | object | One entry per class; the key is the class identifier used by the reader. |

Fields of each entry in `classes`:

| Field | Required | Type | Meaning |
| --- | --- | --- | --- |
| `original` | Yes | text | Label exactly as the dataset names it, including author or typos (`Salix sinerea`). Never corrected. |
| `family` | Yes | text | Plant family. |
| `genus` | Yes | text | Genus. |
| `species` | No | text or `null` | Canonical binomial (`Genus epithet`); must start with the genus. `null` when the class only reaches genus level. |
| `variant` | No | text or `null` | Cultivar or variety separated from the species name (`Sericea`). |
| `status` | Yes | text | Review status, see below. |
| `note` | No | text | Free text: common name, corrections made, doubts. `verify_mapping.py --apply` appends `GBIF: ...` when review is needed. |

Class identifiers: for Swedish Leaf, the class number inside the file name (`l9nr003.tif`
is class `9`). For Flavia, the key given by `label_ranges.csv`.

Values of `status`:

| Value | Meaning |
| --- | --- |
| `proposed_unverified` | Drafted by hand or with an assistant; not checked against a taxonomic authority. |
| `verified` | GBIF returns the same accepted name and agrees on genus and family. See [label_verification_analysis.md](label_verification_analysis.md) for what this does and does not guarantee. |
| `needs_review` | GBIF reports a synonym, a family or genus disagreement or no species-level match; the reason is in `note`. A person decides. |

Validation when the file is loaded: `original`, `family`, `genus` and `status` must be
non-empty, `status` must be one of the three values, and `species` must belong to `genus`.
Otherwise loading fails with a `MappingError`.

## 3. `label_ranges.csv`

Flavia only. The dataset gives no label per file; the authors publish a table that assigns
ranges of image numbers to classes.

| Column | Type | Meaning |
| --- | --- | --- |
| `first_id` | integer | First image number of the range (inclusive). |
| `last_id` | integer | Last image number of the range (inclusive). |
| `key` | text | Class identifier, a key of `classes` in `label_mapping.json`. |

Rule: ranges must not overlap and `first_id` must not exceed `last_id`.

## 4. `images.csv`

One row per image. The same 20 columns are used by every dataset, which is what makes the
datasets combinable. Rows are ordered by class and then by image number.

| Column | Type | Meaning | Example |
| --- | --- | --- | --- |
| `image_id` | text | Unique identifier across datasets: `<source_dataset>:<source_image_id>`. | `flavia:1001` |
| `source_dataset` | text | Dataset name. | `flavia` |
| `source_image_id` | text | File name without extension, lower case. | `1001` |
| `file_path` | text | Path of the image relative to `datasets/<name>/raw/`, with `/`. | `leaves/1001.jpg` |
| `original_label` | text | The `original` field of the mapping entry. | `Phyllostachys edulis (Carr.) Houz.` |
| `family` | text | Unified family. | `Poaceae` |
| `genus` | text | Unified genus. | `Phyllostachys` |
| `species` | text | Unified species; **empty** for genus-only classes. | `Phyllostachys edulis` |
| `mapping_status` | text | `status` of the mapping entry (section 2). | `verified` |
| `organ` | text | Plant organ shown. Always `leaf` for these datasets. | `leaf` |
| `capture_type` | text | How the image was taken: `scan` (Swedish Leaf) or `scan_or_camera` (Flavia, scanned or photographed). | `scan_or_camera` |
| `background` | text | Background type; `plain` for both datasets. | `plain` |
| `width` | integer | Width in pixels. **Empty unless** `--size` is used. | `1600` |
| `height` | integer | Height in pixels. **Empty unless** `--size` is used. | `1200` |
| `sha256` | text | SHA-256 of the file. **Empty unless** `--hash` is used; **mandatory in final versions** (section 13). | `3d4c4730...3477eba` |
| `source_version` | text | Release of the source dataset (`2015`, `v2`), or `unversioned`. | `unversioned` |
| `source_url` | text | Page where the source dataset is published (http or https). | `https://flavia.sourceforge.net/` |
| `license_id` | text | License as a machine-readable identifier: an SPDX id (`CC-BY-4.0`, `CC-BY-NC-4.0`, `CC0-1.0`, ...) or `LicenseRef-<name>` for anything else. `LicenseRef-unspecified` means no license was found. Never free text. | `LicenseRef-unspecified` |
| `redistribution` | text | May the image be redistributed? `allowed`, `not_allowed` or `unknown`. `allowed` is not accepted together with an unspecified license. | `unknown` |
| `attribution` | text | Credit or citation that users of the image must give. Required unless the license is `CC0-1.0`. | `Wu et al. (2007) ...` |

Notes:

- `family`, `genus` and `species` always follow the hierarchy: the species belongs to the
  genus and the genus to the family.
- `capture_type`, `background` and `organ` are the fields that allow domain shift between
  datasets to be studied.
- The five provenance columns (`source_version` to `attribution`) are filled from the dataset's
  `dataset.json` (section 10), so they can be filtered and validated automatically. A source that
  licenses each image separately (for example Pl@ntNet) fills them per image instead.
- `mapping_status` travels with every image so that a model can be trained only on
  `verified` labels.

## 5. `problems.txt`

Written next to `images.csv` only when some files could not be labelled. One line per
problem: `<relative path>: <reason>`. Reasons:

| Reason | Meaning |
| --- | --- |
| `unexpected file name` | The name does not follow the dataset convention (Swedish Leaf). |
| `class N not in mapping` | The class number found in the name has no entry in the mapping. |
| `file name is not a number` | Flavia file whose name is not numeric. |
| `number N is outside every range` | Flavia image number not covered by `label_ranges.csv`. |
| `key 'K' not in mapping` | The range table points to a class missing from the mapping. |

The file does not exist when there are no problems. Files that cause a problem are **not**
included in `images.csv`; nothing is dropped silently.

## 6. `gbif_report.csv`

Result of checking each mapping entry against the GBIF Backbone Taxonomy. One row per class.

| Column | Type | Meaning |
| --- | --- | --- |
| `key` | text | Class identifier (section 2). |
| `original` | text | Original label of the class. |
| `status` | text | Verdict: `verified` or `needs_review`. |
| `gbif_name` | text | Canonical name GBIF matched (may be a family or class name when the match is only at a higher rank). |
| `gbif_status` | text | GBIF taxonomic status of that name: `ACCEPTED`, `SYNONYM`, `DOUBTFUL`, ... |
| `gbif_family` | text | Family that GBIF assigns. |
| `findings` | text | Why the entry needs review, separated by `;`. Empty when verified. |

The rules behind the verdict are in [label_verification_analysis.md](label_verification_analysis.md).

## 7. Combined `images.csv`

Same 20 columns as section 4 (section 4 defines them). It is the concatenation of the
per-dataset tables, with these rules:

- Datasets are processed in alphabetical order.
- A row is **skipped** and a conflict is reported if its `image_id` already exists, or if
  its family or genus contradicts what another row established for the same species or
  genus.
- If the same taxon is written in two ways (for example differing only in case or spacing),
  both rows are kept and a conflict is reported.
- The command exits with status `2` when any conflict exists.
- When a frozen class index is used (`--version`, section 11), three integer columns are
  appended: `family_id`, `genus_id` and `species_id` (`-1` when the species is unknown). They are
  the ids a model must use as targets.

## 8. `taxonomy.csv`

One row per class of the unified taxonomy, with the number of images contributed by each
dataset.

| Column | Type | Meaning |
| --- | --- | --- |
| `family` | text | Family. |
| `genus` | text | Genus. |
| `species` | text | Species. **Empty** means a genus-only class: images that the source labels only with the genus. |
| `family_id`, `genus_id`, `species_id` | integer | Only with a frozen class index (section 11). Ids of the class at each level; `species_id` is `-1` for a genus-only class. |
| `n_<dataset>` | integer | **Number of images** of that row in the dataset `<dataset>`. One column per dataset, in alphabetical order (`n_flavia`, `n_swedish_leaf`). `0` means the dataset has no images of that taxon. |

Example from the local data:

```text
family,genus,species,n_flavia,n_swedish_leaf
Sapindaceae,Acer,,0,75
Sapindaceae,Acer,Acer buergerianum,53,0
Sapindaceae,Acer,Acer palmatum,56,0
```

How to read it: *Acer* appears in both datasets, but Swedish Leaf only labels it at genus
level (75 images, empty `species`), while Flavia has two species of the genus (53 and 56
images). A model trained on both can be compared at genus level, but not at species level.

Properties:

- Each image of `images.csv` is counted in exactly one row, so the sum of a column `n_<dataset>`
  equals the number of images of that dataset in the combined table. This is checked by an
  automated test.
- Rows are sorted by family, genus and species; the genus-only row comes first within its genus.
- A taxon counts as shared between datasets when more than one `n_<dataset>` is greater than
  zero in its row.
- Only classes whose images exist locally appear. If a dataset is partly downloaded, the
  missing classes have no row.

## 9. Integer labels for training

`Taxonomy.encode(species)` and `Taxonomy.encode_label(genus)` (module
`leaf_mlops.data.taxonomy`) turn names into integers for a multi-task classifier, one
output per level:

| Level | Value |
| --- | --- |
| `family`, `genus`, `species` | Position of the class in the **alphabetically sorted** list of classes of that level (`Taxonomy.classes(level)`), starting at 0. |
| Unknown species (genus-only class) | `-1`, which is the default `ignore_index` of the cross-entropy loss in PyTorch, so the sample still trains the family and genus outputs. |

Important: these indices depend on the set of classes. Adding a class can shift the others, which
would silently break any trained model. For anything that is trained or published, use the frozen
class index (section 11) instead of `Taxonomy.encode`.

## 10. `dataset.json`

Provenance and license of one source dataset, in `datasets/<name>/dataset.json`. It is the only
place where this information is written; the readers copy it into every row of `images.csv`.
Loading fails with a `ProvenanceError` if a rule below is broken.

| Field | Required | Type | Meaning |
| --- | --- | --- | --- |
| `name` | Yes | text | Dataset name; must equal the folder name. |
| `source_version` | Yes | text | Release of the source, or `unversioned`. For Pl@ntNet / PlantCLEF this is the year or version, so that the choice of release is recorded. |
| `source_url` | Yes | text | `http(s)` address of the dataset page. |
| `license_id` | Yes | text | SPDX id from the accepted list, or `LicenseRef-<letters, digits, . and ->`. |
| `redistribution` | Yes | text | `allowed`, `not_allowed` or `unknown`. |
| `attribution` | Yes (except `CC0-1.0`) | text | Credit or citation text. |
| `capture_type` | Yes | text | How images were taken (`scan`, `scan_or_camera`, `field`, ...). |
| `background` | Yes | text | Background type (`plain`, `natural`, ...). |
| `license_note` | No | text | Human explanation of the license. Documentation only: it is never used for filtering. |

Accepted SPDX ids: `CC0-1.0`, `CC-BY-3.0`, `CC-BY-4.0`, `CC-BY-SA-4.0`, `CC-BY-NC-4.0`,
`CC-BY-NC-SA-4.0`. The list is in `leaf_mlops.data.provenance` and is extended when a source needs
another one. Commercial use is reported as allowed only for these ids when they are not `NC`.

## 11. `class_index.json`

The frozen link between each class and its integer id, written once per dataset version in
`datasets/releases/<version>/class_index.json` and kept in Git.

| Field | Type | Meaning |
| --- | --- | --- |
| `format` | integer | Format number of this file (currently `1`). |
| `version` | text | Dataset version this index belongs to. |
| `ignore_index` | integer | Id used for an unknown species (`-1`). |
| `fingerprint` | text | SHA-256 of the three class lists. Record it with every trained model: two models can share targets only if their fingerprints are equal. |
| `levels` | object | For `family`, `genus` and `species`: an object `class name -> id`. Ids go from 0 without gaps. |

Rules:

- The first run of `build_combined.py --version V` creates the file. Every later run with the same
  version checks the data against it and **stops** (exit code 1) if the data has a class that is not
  in the index. A frozen version never changes: a different set of classes needs a new version.
- A class in the index without images in a build keeps its id reserved (reported, not an error).
- Editing the file by hand is detected through the fingerprint when it is loaded.
- Ids are alphabetical positions at the moment of freezing. They are fixed from then on, even if
  the alphabetical order of a later taxonomy would differ.
- Create it only when the taxonomy is final for that version (labels reviewed, all datasets
  complete): a provisional index would freeze provisional names.

## 12. `report.md` and `report.json`

Generated by every run of `build_combined.py`; `report.json` has the same content as `report.md` in
machine-readable form. The report is deterministic (no timestamps), so two reports of the same data
are identical and differences between versions are visible in Git. With `--version V` a copy is
written to `datasets/releases/V/`.

| Section | Content |
| --- | --- |
| Size | Images, datasets, families, genera, species and genus-only classes; images and classes per dataset. |
| Class distribution | Images per class (minimum, median, maximum, imbalance ratio = maximum / minimum), classes below 20 images, and a table of every class with its count per dataset. |
| Pending review | Images by `mapping_status`, and the original labels whose status is not `verified`. |
| Licenses | Images by `license_id` and `redistribution`, and whether commercial use is allowed. |
| Capture conditions | Images by dataset, `capture_type` and `background`. |
| Integrity | Images without `sha256`, images without width and height, and groups of identical files stored under different ids. |
| Overlap between datasets | Species or genus-only classes and genera that appear in more than one dataset. |
| Class index | Version, fingerprint and reserved classes without images (only with a frozen index). |
| Conflicts | Taxonomy or identifier contradictions found while combining. |

## 13. Rules for final dataset versions

A build can be explored freely, but a version that is going to be used for training or published
must be traceable and fixed. `build_combined.py --version V --release` checks this and prints one
`NOT RELEASABLE:` line for each failed rule, with exit code 3:

| Rule | Why |
| --- | --- |
| Every image has a `sha256`. Build the tables with `build_interim.py --hash`. | The row is tied to the exact bytes it was made from; without the hash a changed or swapped file goes unnoticed. |
| No two `image_id` share the same `sha256`. | The same photo under two ids can end up in both the training and the test split. |
| A frozen class index exists and the data matches it. | Class ids cannot move between the data and the models. |
| No conflicts were found while combining. | The taxonomy is consistent across sources. |
| Every image has `mapping_status = verified`. | No label in a final version depends on an unchecked name. |
| `license_id`, `redistribution`, `attribution` and `source_url` pass the rules of section 10 for every image. | License and provenance can be filtered and audited automatically. |

Hashes also allow the files to be checked later: `scripts/verify_integrity.py datasets/combined/images.csv`
re-hashes the raw images and reports files that changed or disappeared (exit code 2).
