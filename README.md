# leaf_mlops

MLOps platform for creating, annotating, versioning and managing tree-leaf image datasets
for AI and computer vision applications. Final Degree Project (TFG), Universidad
Complutense de Madrid.

The platform is shared with two other TFGs (classification and segmentation of tree
species), and the datasets it produces are meant to be reused by external researchers.
Its first job is to turn several heterogeneous leaf datasets into one coherent, traceable
dataset with a unified family / genus / species hierarchy.

## Status

| Area | State |
| --- | --- |
| Dataset readers (Swedish Leaf, Flavia) into a common table | Done |
| Scientific-name normalisation and per-dataset label mappings | Done |
| Mapping verification against the GBIF Backbone | Done (reports in `datasets/<name>/gbif_report.csv`) |
| Combined cross-dataset table with taxonomy conflict checks | Done |
| Storage abstraction (local file system, S3-compatible) | Done |
| Web application, database models, review workflow, versioned exports | Planned (Django) |
| Pl@ntNet / PlantCLEF reader | Planned (release to be fixed first) |

## Documentation

- [docs/running_and_testing.md](docs/running_and_testing.md): how to run and check every part of the code, step by step.
- [docs/data_formats.md](docs/data_formats.md): meaning of every column and field of the files the project reads and writes.
- [docs/requirements.md](docs/requirements.md): functional and non-functional requirements.
- [docs/platform_survey.md](docs/platform_survey.md): technology selection derived from the requirements.
- [docs/dataset_survey.md](docs/dataset_survey.md): candidate datasets, licences, label unification results and gap analysis.
- [docs/label_verification_analysis.md](docs/label_verification_analysis.md): results of checking the label mappings against GBIF, and why some entries fail.
- [datasets/README.md](datasets/README.md): dataset layout and the ingestion workflow.

## Repository layout

```
src/leaf_mlops/
    data/       Readers, name normalisation, taxonomy, label mapping, GBIF check, combine
    storage/    Storage interface with local and S3-compatible backends
scripts/        Command-line entry points (build_interim, verify_mapping, build_combined)
datasets/       One directory per dataset: label mapping and reports are versioned, images are not
tests/          Automated tests (no network or accounts needed)
docs/           Requirements and surveys
report/         LaTeX thesis
```

## Installation

### Linux / macOS

```bash
git clone https://github.com/KaTVasq/leaf_mlops.git
cd leaf_mlops
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

### Windows (PowerShell)

```powershell
git clone https://github.com/KaTVasq/leaf_mlops.git
cd leaf_mlops
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

If PowerShell blocks the activation script, run
`Set-ExecutionPolicy -Scope Process RemoteSigned` first.

Run the tests (no cloud account, bucket or network is required):

```bash
python -m pytest
```

## Usage

Place the raw images under `datasets/<name>/raw/` (see [datasets/README.md](datasets/README.md)
for where to download them), then:

```bash
python scripts/build_interim.py swedish_leaf        # one metadata row per image
python scripts/build_interim.py flavia
python scripts/verify_mapping.py flavia             # check the label mapping against GBIF
python scripts/build_combined.py swedish_leaf flavia  # unified table and taxonomy
```

`verify_mapping.py` needs internet access and writes a report; add `--apply` to store the
resulting status in the mapping file. It never changes family, genus or species.

## Configuration

Storage is selected with environment variables; copy `.env.example` to `.env` to change
them. The default (`STORAGE_BACKEND=local`, `MEDIA_ROOT=./data/media`) needs nothing else.
S3-compatible storage (MinIO, Cloudflare R2, AWS S3) is optional:

```bash
pip install -e ".[s3]"
```

```python
from leaf_mlops.storage import get_storage

storage = get_storage()                 # reads STORAGE_BACKEND and friends
storage.save("flavia/1001.jpg", data)
with storage.open("flavia/1001.jpg") as handle:
    ...
```

## Licences and data

Raw images are **not** committed: several datasets have no explicit licence or restrict
redistribution (see the licence section of the dataset survey). The repository contains code,
label mappings and reports only.

## Thesis report

The LaTeX source is in `report/`.
