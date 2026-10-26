# Running and testing the code

Step-by-step guide to run every part of the project and check that it works. Each section
says what it does, the command, what you should see and what to do if you do not.

Commands assume the repository root as working directory. Outputs were taken from a real
run on Windows (paths use `\` there; Linux and macOS show `/`). Numbers such as image counts
depend on which raw files you have downloaded.

| Section | What it checks | Needs internet | Needs raw images |
| --- | --- | --- | --- |
| [1. Set-up](#1-set-up) | The package installs | Yes (once) | No |
| [2. Automated tests](#2-automated-tests) | All logic, with fake data | No | No |
| [3. Code style](#3-code-style) | Linter | No | No |
| [4. Name normalisation](#4-name-normalisation) | Parsing of scientific names | No | No |
| [5. Label mapping and taxonomy](#5-label-mapping-and-taxonomy) | Mapping files, hierarchy, integer labels | No | No |
| [6. Dataset to table](#6-dataset-to-table-build_interimpy) | Readers | No | Yes |
| [7. GBIF verification](#7-gbif-verification-verify_mappingpy) | Mapping against GBIF | Yes (first time) | No |
| [8. Combining datasets](#8-combining-datasets-build_combinedpy) | Cross-dataset table and conflicts | No | Yes |
| [9. Storage](#9-storage) | Local and S3-compatible storage | Only for S3 | No |

## 1. Set-up

Create a virtual environment and install the package with the development tools.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

On Windows PowerShell use `py -m venv .venv` and `.venv\Scripts\Activate.ps1` instead.
Python 3.10 or newer is required.

**Check:**

```bash
python -c "import leaf_mlops; print('ok')"
```

It should print `ok`. If you get `ModuleNotFoundError: No module named 'leaf_mlops'`, the
environment is not active or `pip install -e ".[dev]"` was not run in this folder.

## 2. Automated tests

```bash
python -m pytest
```

Expected: `65 passed`. No internet, no accounts and no raw images are needed: tests use
temporary folders and a fake GBIF and a fake S3 client.

Run one area at a time when something fails:

| File | Tests | What it covers |
| --- | --- | --- |
| `tests/test_names.py` | 8 | Name parsing and normalisation, typo suggestions |
| `tests/test_taxonomy.py` | 7 | Hierarchy, integer labels, inconsistent parents |
| `tests/test_mapping.py` | 7 | Mapping file validation and taxonomy building |
| `tests/test_readers.py` | 5 | Swedish Leaf and Flavia readers, problem reporting |
| `tests/test_gbif.py` | 9 | GBIF decisions (verified or review), cache, writing back |
| `tests/test_combine.py` | 7 | Merging datasets, conflicts, overlap |
| `tests/test_storage.py` | 22 | Local and S3 backends with the same tests, unsafe keys, configuration |

```bash
python -m pytest tests/test_gbif.py          # one file
python -m pytest tests/test_gbif.py -v       # list every test
python -m pytest -k hybrid                   # tests whose name contains "hybrid"
python -m pytest -x                          # stop at the first failure
```

## 3. Code style

```bash
python -m ruff check .
```

Expected: `All checks passed!`. The rules are fixed in `pyproject.toml`, and the same command
runs in the CI workflow `.github/workflows/tests.yml`.

## 4. Name normalisation

Scientific names for the same taxon are written in different ways. Try the helpers:

```bash
python -c "
from leaf_mlops.data.names import parse_name, normalize_key, suggest_names
p = parse_name('Populus ×canadensis Moench')
print(p.canonical, p.is_hybrid)
q = parse_name(\"salix_alba 'Sericea'\")
print(q.canonical, q.cultivar)
print(normalize_key('Fagus  Silvatica'))
print(suggest_names('Fagus silvatica', ['Fagus sylvatica', 'Quercus robur']))
"
```

Expected:

```text
Populus canadensis True
Salix alba Sericea
fagus silvatica
['Fagus sylvatica']
```

The hybrid sign and the author are removed, the quoted cultivar is split off, and the typo
`silvatica` is matched with `sylvatica`. These helpers only describe differences; they never
decide a taxonomic question.

## 5. Label mapping and taxonomy

Each dataset has `datasets/<name>/label_mapping.json`: original class, family, genus,
species and a review status. Load one and build the hierarchy:

```bash
python -c "
from leaf_mlops.data.mapping import load_label_mapping, build_taxonomy
t = build_taxonomy(load_label_mapping('datasets/swedish_leaf/label_mapping.json'))
print(t.classes('family'))
print(t.encode('Ulmus glabra'))
print(t.encode_label('Acer'))
"
```

Expected:

```text
['Betulaceae', 'Fagaceae', 'Malvaceae', 'Rosaceae', 'Salicaceae', 'Sapindaceae', 'Ulmaceae']
{'family': 6, 'genus': 9, 'species': 10}
{'family': 5, 'genus': 0, 'species': -1}
```

The last line is a class that only reaches genus level (*Acer*): the species label is `-1`
(ignore index), not an invented species.

**Try to break it.** Edit a copy of the mapping so that a species is not in its genus
(for example `"genus": "Quercus"` for `Ulmus glabra`). Loading must fail with a
`MappingError`. The same applies to an unknown `status` or an empty family.

## 6. Dataset to table (`build_interim.py`)

Converts the raw files of one dataset into a table with one row per image. It does not
modify or move the raw files.

**Requires** the downloaded images in `datasets/<name>/raw/` (see
[datasets/README.md](../datasets/README.md) for the layout).

```bash
python scripts/build_interim.py swedish_leaf
python scripts/build_interim.py flavia
```

Expected for the local copy used when writing this guide:

```text
150 images written to datasets\swedish_leaf\interim\images.csv
Taxonomy: 7 families, 10 genera, 11 species
  Acer: 75
  Ulmus carpinifolia: 75
Classes in the mapping without images: Salix aurita, Quercus, ...
```

Flavia gives `1907 images`. Open `datasets/<name>/interim/images.csv` to inspect the rows.

How to read the output:

- **"Classes in the mapping without images"** is not an error: that part of the dataset is
  not in your `raw/` folder. The local Swedish Leaf copy has 2 of 15 classes.
- **`WARNING: N mapping entries are not verified yet`** means some entries are not
  `verified` (section 7).
- **`problems.txt`** (in `interim/`) lists files that could not be labelled, such as an
  unexpected file name. An empty or missing file is good.
- **`ERROR: ... does not exist`** means the `raw/` folder is missing or in the wrong place.

Optional flags: `--hash` computes the SHA-256 of every image and `--size` reads width and
height (needs Pillow, installed with `[dev]`). Both are slower.

## 7. GBIF verification (`verify_mapping.py`)

Checks every mapping entry against the GBIF Backbone Taxonomy and reports synonyms, family
disagreements and names it cannot place. Background and interpretation are in
[label_verification_analysis.md](label_verification_analysis.md).

```bash
python scripts/verify_mapping.py swedish_leaf
python scripts/verify_mapping.py flavia
```

Expected:

```text
swedish_leaf: 14 verified, 1 need review
  [14] Sorbus intermedia: GBIF match is HIGHERRANK ('Rosaceae'); GBIF rank is FAMILY, expected SPECIES
Report: datasets\swedish_leaf\gbif_report.csv
```

```text
flavia: 28 verified, 4 need review
```

- The first run needs internet and takes a few seconds. Answers are cached in
  `datasets/_cache/gbif.json`, so later runs work offline.
- If GBIF changed since the guide was written, the numbers can differ. That is a result, not a
  bug: read `gbif_report.csv`.
- `ERROR: GBIF request failed` means no connection or the API is down.

**By default nothing in the mapping is modified**, only the report is written. With
`--apply` the script also writes `status` and `note` into `label_mapping.json`. Commit or
copy the file first so you can compare with `git diff`.

### Check that it detects mistakes

Work on a temporary copy so the real mapping is not touched. This changes the family of
*Ulmus* to a wrong one:

```bash
mkdir -p /tmp/check/swedish_leaf
sed 's/"family": "Ulmaceae"/"family": "Fagaceae"/' datasets/swedish_leaf/label_mapping.json > /tmp/check/swedish_leaf/label_mapping.json
python scripts/verify_mapping.py swedish_leaf --datasets-dir /tmp/check
```

Expected: the two *Ulmus* classes appear as needing review, for example
`GBIF family is 'Ulmaceae', mapping has 'Fagaceae'`. If they were still `verified`, the check
would be useless.

## 8. Combining datasets (`build_combined.py`)

Merges the tables of several datasets into one table and one taxonomy, and reports
contradictions between datasets. Run section 6 for each dataset first.

```bash
python scripts/build_combined.py swedish_leaf flavia
```

Expected for the local copy:

```text
2057 images from 2 datasets written to datasets\combined
Taxonomy: 22 families, 30 genera, 33 species
Taxa present in more than one dataset: 0
Genera present in more than one dataset: 1
  Acer: flavia=109, swedish_leaf=75
```

Outputs in `datasets/combined/`:

- `images.csv`: all rows with the common columns.
- `taxonomy.csv`: one row per species or genus-only class. The columns `n_flavia` and
  `n_swedish_leaf` are the **number of images** of that row in each dataset. Every column
  definition is in [data_formats.md](data_formats.md).

The overlap counts only the classes whose images are present locally. With the full
Swedish Leaf the two datasets share two genera (*Acer*, *Populus*).

Exit codes: `0` means no conflicts, `2` means taxonomy conflicts were found and printed as
`CONFLICT: ...` (for example the same species with two different families in two datasets),
and `1` means a missing input such as
`ERROR: datasets\nope\interim\images.csv not found`.

## 9. Storage

The application talks to a storage interface (`save`, `open`, `exists`, `delete`,
`list_keys`). The backend is chosen with environment variables; the default is a local
folder and needs nothing installed.

### 9.1 Local file system

```bash
python -c "
import tempfile, os
from leaf_mlops.storage import get_storage
d = tempfile.mkdtemp()
s = get_storage({'STORAGE_BACKEND': 'local', 'MEDIA_ROOT': os.path.join(d, 'media')})
s.save('flavia/1001.jpg', b'hola')
print(s.exists('flavia/1001.jpg'), s.list_keys('flavia/'), s.open('flavia/1001.jpg').read())
s.save('../fuera.jpg', b'x')
"
```

Expected: the first line is `True ['flavia/1001.jpg'] b'hola'`, and then the script stops
with `StorageError: Invalid storage key: '../fuera.jpg'`. Keys that try to leave the storage
folder are rejected on purpose.

To use it with a `.env` file, copy `.env.example` to `.env` and keep
`STORAGE_BACKEND=local`.

### 9.2 S3-compatible storage (optional)

The S3 backend is tested automatically with a fake client (section 2), so you do not need
an account for the tests. To try it against a real server you need `boto3` and an
S3-compatible service, for example MinIO.

> The steps below were **not run** while writing this guide, because they need Docker and
> `boto3`. Treat them as a checklist and report anything that does not work.

```bash
pip install -e ".[s3]"
docker run -p 9000:9000 -p 9001:9001 minio/minio server /data --console-address ":9001"
```

Create a bucket named `leaf-images` in the MinIO console (`http://localhost:9001`), then set
in `.env`:

```text
STORAGE_BACKEND=s3
S3_BUCKET=leaf-images
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY_ID=<MinIO user>
S3_SECRET_ACCESS_KEY=<MinIO password>
```

Then run the same Python snippet as in 9.1 passing these variables. The result must be
identical. Never commit `.env`: it is ignored by Git.

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `ModuleNotFoundError: leaf_mlops` | Environment not active, or package not installed | Activate `.venv`, run `pip install -e ".[dev]"` |
| `python -m pytest` collects 0 tests | Wrong folder | `cd` to the repository root |
| `ERROR: ... raw does not exist` | Dataset not downloaded | See `datasets/README.md` |
| `ERROR: GBIF request failed` | No internet or API down | Retry; if the cache exists, use it |
| `CONFLICT:` and exit code 2 | Datasets disagree on a family or genus | Fix the mapping entries involved |
| PowerShell refuses to activate `.venv` | Execution policy | `Set-ExecutionPolicy -Scope Process RemoteSigned` |
