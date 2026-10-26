# Requirements

Requirements of the platform for creating, annotating, versioning and managing tree-leaf
image datasets. The technology choices in [platform_survey.md](platform_survey.md) are
derived from this document, not the other way round.

- **Last updated:** 26/10/2026
- **Priority** uses MoSCoW: **M**ust, **S**hould, **C**ould. *Won't (now)* items are listed
  at the end.
- **Source** says where each requirement comes from, so it can be traced in the report:
  *Project* (original proposal), *Tutor* (feedback on the repository), *Meeting* (latest
  team meeting with the other TFG students), *Survey* ([dataset_survey.md](dataset_survey.md)).

## 1. Context and stakeholders

The platform manages the whole life cycle of a leaf-image dataset that researchers
(including a group at UC Davis) will later use to train and evaluate their own models. Three
TFGs share it:

| Stakeholder | What they need from the platform |
| --- | --- |
| Hierarchical classification (family, genus, species) | One label scheme across several datasets, the full hierarchy, reproducible train/validation/test splits, metadata to study domain shift (train on one dataset, test on another). |
| Segmentation | Original images plus a place to store masks (background removal), and to compare segmenters on the same images. |
| Morphological and frequency descriptors | A way to attach per-image numeric features (circularity, width, length, Feret diameters, Fourier descriptors) computed from images or masks, and to export them with the labels. |
| External researchers | A documented export format, stable identifiers, clear licenses and provenance. |
| This TFG (platform) | A system that one person can build, test, deploy and defend in the report. |

## 2. Functional requirements

| ID | Requirement | Priority | Source |
| --- | --- | --- | --- |
| FR-01 | Ingest a dataset through a reader that converts its own layout into a common table with one row per image, without modifying the raw files. Files that cannot be labelled are reported, not dropped silently. | M | Project, Survey |
| FR-02 | Keep provenance for every image: source dataset and version, source image id, author, license, SHA-256 of the file. | M | Survey, Meeting |
| FR-03 | Unify labels across datasets: normalise scientific names (case, hyphens, authorities, hybrids), keep a reviewable mapping per dataset from original label to canonical name, and mark each entry as verified, proposed or needing review. | M | Meeting |
| FR-04 | Check the mapping against a taxonomic authority (GBIF Backbone) and report synonyms, family disagreements and unknown names. Taxonomy is never changed automatically. | M | Meeting, Tutor |
| FR-05 | Derive family and genus from the species and support classes that only reach genus level (for example "Acer" in Swedish Leaf). | M | Project, Meeting |
| FR-06 | Store capture metadata per image so that domain shift can be studied: capture type (scan, field photo), background, organ, resolution and whether the sample is a simple or compound leaf. Samples are labelled, not filtered out. | M | Meeting |
| FR-07 | Store annotation layers as separate objects linked to an image: segmentation masks, morphological features, frequency descriptors. Each layer records the tool and version that produced it, so layers from different TFGs can be added later. | M | Meeting |
| FR-08 | Create immutable dataset versions from a recipe (sources, filters, splits). A version can be rebuilt and traced back to the original images. | M | Project, Tutor |
| FR-09 | Filter and select subsets by dataset, organ, license, taxonomic level, capture type or review status. | M | Survey |
| FR-10 | Export a version in documented, machine-readable files (CSV or Parquet plus images), with integer labels for family, genus and species and an "ignore" value for unknown levels. | M | Project, Meeting |
| FR-11 | Report which species and genera appear in more than one dataset (the pairs that cross-dataset experiments need). | S | Meeting |
| FR-12 | Select the image storage backend by configuration (local file system by default, S3-compatible optionally) without changing application code. | M | Tutor |
| FR-13 | Review and correct labels in a web interface, keeping an audit trail of who changed what and when. | S | Project, Survey |
| FR-14 | Users with roles (administrator, reviewer, read-only). | S | Project |
| FR-15 | Upload a new image, remove sensitive EXIF data (for example GPS) and store it with its provenance. | C | Project |
| FR-16 | Run a trained classifier on an uploaded image and store the prediction with its confidence. | C | Project |
| FR-17 | Register data augmentation or preprocessing recipes (for example white background) as derived versions rather than overwriting originals. | C | Meeting |

## 3. Non-functional requirements

| ID | Requirement | Priority | Source |
| --- | --- | --- | --- |
| NFR-01 | **Reproducible set-up:** a person who clones the repository can install it and run the tests without creating any cloud account, bucket or credentials. | M | Tutor |
| NFR-02 | **Licensing:** the repository never contains raw images of datasets with unclear or restrictive licenses. Only mappings, reports and code are versioned. | M | Survey, Meeting |
| NFR-03 | **Scale:** handle at least the size of Pl@ntNet-300K (about 300,000 images, around 30 GB) with filtering and export in reasonable time. | S | Survey |
| NFR-04 | **Traceability:** every exported label can be traced to its source dataset, mapping entry and, if corrected, the correction. | M | Project, Tutor |
| NFR-05 | **Testability:** core logic is covered by automated tests that run without network access (external services are injected). | M | Project |
| NFR-06 | **Maintainability:** built with mainstream, well-documented tools that a single developer can maintain, with typed Python and a linter. | M | Project |
| NFR-07 | **Portability:** runs on Windows, Linux and macOS. | S | Project |
| NFR-08 | **Privacy:** uploaded images are stripped of location metadata before storage. | S | Project |
| NFR-09 | **Language:** code, documentation and exported metadata are in English, because the reuse is international. | M | Project |
| NFR-10 | **Interoperability:** exports do not depend on this platform to be read (open formats). | M | Meeting |

## 4. Decisions still open

These need an answer from the team before the corresponding requirement can be closed.

1. **PlantCLEF / Pl@ntNet version.** The group has been using PlantCLEF 2015, while newer
   releases exist. A written justification of the chosen year is pending; the version must
   then be fixed in the dataset records (FR-02, FR-08).
2. **Common dataset subset.** Which datasets the three TFGs will share for cross-dataset
   experiments. Only datasets with a clear license should be included (NFR-02).
3. **Simple versus compound leaves.** Decision so far: do not filter, store the attribute (FR-06).
4. **Where masks and features are produced.** The segmentation and descriptor TFGs
   produce them; this platform only stores and versions them (FR-07). The exchange format
   (for example PNG masks named after `image_id`, one CSV per feature set) must be agreed.
5. **Frequency descriptors.** Which ones are worth storing (dominant frequency band,
   angular sweep) is still being explored by the tutors.

## 5. Won't do (for now)

- A full in-browser annotation tool with drawing of polygons: segmentation is produced by
  models or external tools and imported (FR-07).
- Training and hyper-parameter search of classifiers: those belong to the other TFGs.
- Explainability (Grad-CAM) and CNN feature-space analysis: kept for a second phase, once
  the datasets are ready.
