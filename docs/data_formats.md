# Data formats

Definition of every file the project reads or writes: what each column or field means, which
values it can take and how it is produced. It is the reference for people who use the
exported tables (the other TFGs and external researchers) and the source for the
corresponding chapter of the thesis.

- **Last updated:** 26/10/2026
- **Encoding:** all text files are UTF-8, with `\n` or `\r\n` line ends. CSV files always have a header row.
- **Missing values:** an empty cell means "not available" (never `NA` or `null` in CSV).
- **Example values** come from the Swedish Leaf and Flavia datasets.

## 1. Overview

| File | Location | Produced by | Versioned in Git | Section |
| --- | --- | --- | --- | --- |
| `label_mapping.json` | `datasets/<name>/` | By hand, then `verify_mapping.py --apply` | Yes | [2](#2-label_mappingjson) |
| `label_ranges.csv` | `datasets/flavia/` | By hand | Yes | [3](#3-label_rangescsv) |
| `images.csv` (per dataset) | `datasets/<name>/interim/` | `build_interim.py` | No (generated) | [4](#4-imagescsv) |
| `problems.txt` | `datasets/<name>/interim/` | `build_interim.py` | No (generated) | [5](#5-problemstxt) |
| `gbif_report.csv` | `datasets/<name>/` | `verify_mapping.py` | Yes | [6](#6-gbif_reportcsv) |
| `images.csv` (combined) | `datasets/combined/` | `build_combined.py` | No (generated) | [7](#7-combined-imagescsv) |
| `taxonomy.csv` | `datasets/combined/` | `build_combined.py` | No (generated) | [8](#8-taxonomycsv) |

Data flow:

```text
raw images + label_mapping.json (+ label_ranges.csv)
        │  build_interim.py
        ▼
datasets/<name>/interim/images.csv ──► build_combined.py ──► datasets/combined/images.csv
                                                         └─► datasets/combined/taxonomy.csv
label_mapping.json ──► verify_mapping.py ──► gbif_report.csv
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

One row per image. The same 16 columns are used by every dataset, which is what makes the
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
| `sha256` | text | SHA-256 of the file. **Empty unless** `--hash` is used. | |
| `license` | text | License or citation requirement of the source. Free text, not a controlled vocabulary. | `unspecified; cite Wu et al. 2007` |

Notes:

- `family`, `genus` and `species` always follow the hierarchy: the species belongs to the
  genus and the genus to the family.
- `capture_type`, `background` and `organ` are the fields that allow domain shift between
  datasets to be studied.
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

Same 16 columns as section 4 (section 4 defines them). It is the concatenation of the
per-dataset tables, with these rules:

- Datasets are processed in alphabetical order.
- A row is **skipped** and a conflict is reported if its `image_id` already exists, or if
  its family or genus contradicts what another row established for the same species or
  genus.
- If the same taxon is written in two ways (for example differing only in case or spacing),
  both rows are kept and a conflict is reported.
- The command exits with status `2` when any conflict exists.

## 8. `taxonomy.csv`

One row per class of the unified taxonomy, with the number of images contributed by each
dataset.

| Column | Type | Meaning |
| --- | --- | --- |
| `family` | text | Family. |
| `genus` | text | Genus. |
| `species` | text | Species. **Empty** means a genus-only class: images that the source labels only with the genus. |
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

Important: the indices depend on the set of classes. Adding a class can shift the others.
The class list used for training must therefore be saved together with the model or the
exported dataset version.
