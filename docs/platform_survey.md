# Platform survey

Research on existing platforms and tools that can be used in the project.

- **Last updated:** 08/10/2026
- **Method:** web search of official documentation and papers where possible.

## 1. Functions covered

1. Hosting and publishing datasets
2. Storage and versioning of data and models
3. Annotation and review of labels
4. Collecting contributions from users (citizen science)
5. Services for taxonomy and species identification
6. Building blocks for a custom web platform with user accounts

## 2. Comparison criteria

| Criterion | Why it matters |
|-----------|----------------|
| License flexibility | Source images carry CC BY, BY-SA and BY-NC licenses |
| Size limits | For example, Pl@ntNet-300K alone is about 31.7 GB |
| Access control | Some data cannot be redistributed |
| Citability (DOI) | Needed for the thesis and for collaborators |
| Open source, no lock-in | Reproducibility |

## 3. Dataset hosting and publishing

### 3.1 Hugging Face Hub (datasets)

- **What:** Git-like hosting for datasets with dataset cards, a browser viewer, and a Python
  `datasets` library.
- **Storage:** free storage for public repositories; private repositories get a free tier
  and are billed above it. No per-repository size limit, but uploads count against the
  account quota.
- **Cost:** private storage above the included amount is billed per TB per month. Two
  documentation versions showed different prices (about $18 and $25 per TB/month), so
  **verify on the pricing page**.
- **Access control:** private datasets and gated datasets (users request access).
- **Advantages:** versioning, dataset card, easy loading from training code, organizations
  for collaboration.
- **Drawbacks:** commercial company; no DOI by default; public hosting is redistribution of
  every image.

### 3.2 Zenodo

- **What:** CERN-hosted general research repository, free to upload and download.
- **Limits:** 50 GB per record (max 100 files).
- **Features:** DOI per record plus a top-level DOI for all versions, versioning, GitHub
  integration, closed / embargoed / restricted / open access.
- **Licenses:** many licenses accepted; the depositor must specify one for public files and
  is responsible for respecting the licenses of what is uploaded. Metadata is CC0.
- **Note:** Pl@ntNet-300K is published here.
- **Drawbacks:** no curation, no dataset viewer for images.

### 3.3 Dryad

- **What:** curated repository, preserved in the University of California Merritt
  repository. UC Davis researchers have campus access with up to 300 GB per upload.
- **License:** **all data is published under CC0.**
- **Cost:** a size-based data publishing charge applies unless an institution or publisher
  sponsors it. **Verify** eligibility for a student collaborating with UC Davis.
- **Limitation:** images under BY-SA or BY-NC cannot be relicensed as CC0.

### 3.4 Kaggle Datasets

- **What:** dataset hosting tied to notebooks and competitions.
- **Limits:** private quota reported between about 100 GB and 200 GB depending on source and
  date (**verify** on kaggle.com/docs/datasets).
- **Licenses:** mirroring an external dataset is allowed only when the right license is in place.
- **Drawbacks:** weak support for per-image provenance and license metadata.

## 4. Storage and versioning

### 4.1 DVC (Data Version Control)

- **What:** open-source tool that stores small pointer files in Git and the data in a remote.
  Supported remotes include S3, Google Cloud, Azure, SSH servers and local disks.
- **Advantages:** ties each Git commit to an exact version of the data; supports pipelines.
- **Drawbacks:** extra steps in the README; the remote must be **private** when data cannot
  be redistributed.

### 4.2 MLflow

- **What:** Apache 2.0 platform for experiment tracking and a model registry (versions,
  stage transitions), with a REST API. Free to self-host.
- **Drawbacks:** self-hosting needs a tracking server, a backend database and an artifact store.

### 4.3 Cloudflare R2

- **What:** S3-compatible object storage with **zero egress fees**.
- **Cost found:** free tier of 10 GB-month, 1M Class A and 10M Class B operations per
  month; Standard storage about $0.015 per GB-month beyond that. Operations are still
  metered. **Verify** on the pricing page.

### 4.4 DagsHub storage

- **What:** hosted platform for DVC projects. Its documentation mentions an S3-compatible
  bucket and DVC remote with 10 GB free per repository.
- **Caveat:** that documentation may be outdated; **verify** the current plan and availability.

### 4.5 MinIO and self-hosted S3 storage

- **MinIO:** reports for 2026 say it removed admin features from the community edition in
  2025, stopped publishing binaries and Docker images, entered maintenance mode in
  December 2025 and archived its repository on 2026-04-25.
- **Alternatives named in those reports:** Garage (AGPL-3.0, lightweight), SeaweedFS and
  RustFS (Apache-2.0). Several sources suggest a managed S3 service instead of self-hosting.

## 5. Annotation and review

### 5.1 Label Studio (Community Edition)

- **License:** Apache 2.0. Free to self-host with Docker or pip. SSO and annotator analytics
  are paid features.
- **Features:** multi-modal labeling, REST API, ML backend integration for model
  pre-annotation.

### 5.2 CVAT

- **License:** MIT. Open source and self-hostable.
- **Features:** boxes, polygons, masks, keypoints and video; strong for segmentation.
- **Drawbacks:** heavier to run; some collaboration features are paid when self-hosted.

## 6. Contribution and citizen-science platforms

### 6.1 Zooniverse Project Builder

- **What:** free platform to build crowdsourced image classification projects without coding.
  Supports classification, marking and drawing tasks, tutorials, a discussion forum and data exports.
- **How it works:** the research team uploads the images (subjects); volunteers classify them.
- **Conditions:** public launch requires a beta review; classification data commonly becomes
  open after a proprietary period of about two years.

### 6.2 Pl@ntNet

- **What:** citizen-science platform where users upload and annotate plant observations and
  the AI model proposes species.
- **Validation:** others vote on observations; a label is the aggregation of at least two
  votes; a trust score per user is estimated from agreement with the consensus; observations
  without enough votes are marked as not valid.
- **Training data:** the aggregated labels, not raw predictions, are used to train the model
  (Lefort et al., 2024).
- **Interface:** for each proposed species it also shows similar pictures from its database.
- **Data access:** annual datasets shared through LifeCLEF, validated observations on GBIF,
  and the Pl@ntNet-300K dataset on Zenodo.
- **Not researched:** whether its platform code is available for reuse.

### 6.3 iNaturalist

- **What:** large citizen-science platform with community identification.
- **Licenses:** set per photo; the default photo license is CC BY-NC.
- **Open data:** licensed images are available on AWS without an account.
- **Privacy:** EXIF metadata is stripped from stored photos, and location is hidden when the
  observation is set to obscured or private.
- **Not researched:** whether its platform code is available for reuse.

## 7. Services for taxonomy and identification

### 7.1 Pl@ntNet API

- **Quota:** free up to 500 identification queries per day with an account; attribution
  sentence requested; paid plans for commercial use above the quota.
- **Features:** species routes return genus and family; identification routes return the
  predicted organ per image.
- **Not verified:** whether its predictions may be used as labels in a published dataset;
  read the terms first.

### 7.2 GBIF

- **What:** open taxonomy backbone and occurrence data; used to normalize species names and
  derive genus and family.
- **Licenses:** accepts only CC0, CC BY and CC BY-NC content.

## 8. Building blocks for a custom platform with user accounts (general knowledge, not researched here)

| Layer | Options |
|-------|---------|
| Backend | Django (accounts, admin and permissions included) or FastAPI (lighter, Python ML friendly) |
| Database | PostgreSQL | |
| Frontend | HTMX or React; installable web app (PWA) to use the phone camera |
| Model serving | Model loaded in the backend or a separate service |
| Background jobs | Task queue |
| Image storage | S3-compatible (Cloudflare R2, Backblaze B2, Garage) |
| Deployment | Docker on a VPS or a university server |

## 9. Privacy and license facts relevant to these platforms

| Topic | Finding |
|-------|---------|
| EXIF metadata | Photos can carry GPS position and device make, model or serial number. iNaturalist strips EXIF from stored photos. A Utrecht University citizen-science project (CoastSnap) stores no EXIF and renames files. |
| GDPR | A forum discussion on iNaturalist argues GDPR requires handling such metadata with care and transparency; consult the university data protection office for the real requirements. |
| Dryad | CC0 only: not compatible with BY-SA or BY-NC images |
| Zenodo, Hugging Face | Declared licenses; the depositor is responsible for compliance |
| Combined datasets | The most restrictive license among the images defines what can be released |

## 10. Comparison

| Platform | Function | Cost | Size limit | Licenses | Open source |
|----------|----------|------|-----------|----------|-------------|
| Hugging Face Hub | Host and version datasets | Free public; paid private above tier | Account quota | Declared | No |
| Zenodo | Publish with DOI | Free | 50 GB per record | Many | Yes (Invenio) |
| Dryad | Curated publication | Charge unless sponsored | 300 GB | **CC0 only** | Yes |
| Kaggle | Dataset hosting | Free | ~100-200 GB private | Declared | No |
| DVC | Dataset versioning | Free | Depends on remote | n/a | Yes |
| MLflow | Tracking, model registry | Free | Self-hosted | n/a | Yes (Apache 2.0) |
| Cloudflare R2 | Object storage | 10 GB free, then ~$0.015/GB | None | n/a | No |
| DagsHub | DVC hosting | 10 GB free (verify) | Plan-based | n/a | No |
| MinIO | Object storage | n/a | n/a | n/a | Archived |
| Label Studio CE | Annotation | Free | Self-hosted | n/a | Yes (Apache 2.0) |
| CVAT | Annotation, segmentation | Free | Self-hosted | n/a | Yes (MIT) |
| Zooniverse | Crowd classification | Free | n/a | n/a | n/a |
| Pl@ntNet | Citizen science, identification | Free | n/a | Per image | Not verified |
| iNaturalist | Citizen science, open data | Free | n/a | Per photo | Not verified |
| Pl@ntNet API | Identification, taxonomy | 500 queries/day free | n/a | n/a | No |
| GBIF | Taxonomy, occurrences | Free | n/a | CC0, BY, BY-NC | n/a |

## 11. Items to verify

- Current Hugging Face private storage price, Kaggle quota and DagsHub plan.
- Pl@ntNet API terms on using predictions as dataset labels.
- Availability of Pl@ntNet and iNaturalist platform code.
- Whether Zenodo's 50 GB limit can be raised for larger records -> Zenodo says to contact them.
