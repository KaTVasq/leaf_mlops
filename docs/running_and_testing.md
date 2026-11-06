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
| [8. Combining datasets](#8-combining-datasets-build_combinedpy) | Cross-dataset table, conflicts, report, frozen class ids, final-version check | No | Yes |
| [9. Storage](#9-storage) | Local and S3-compatible storage | Only for S3 | No |
| [10. Provenance and license](#10-provenance-and-license-datasetjson) | `dataset.json` rules | No | No |
| [11. Integrity](#11-integrity-sha-256-hashes) | Hashes of the images | No | Yes |

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

Expected: `101 passed`. No internet, no accounts and no raw images are needed: tests use
temporary folders and a fake GBIF and a fake S3 client.

Run one area at a time when something fails:

| File | Tests | What it covers |
| --- | --- | --- |
| `tests/test_names.py` | 8 | Name parsing and normalisation, typo suggestions |
| `tests/test_taxonomy.py` | 7 | Hierarchy, integer labels, inconsistent parents |
| `tests/test_mapping.py` | 7 | Mapping file validation and taxonomy building |
| `tests/test_readers.py` | 6 | Swedish Leaf and Flavia readers, problem reporting, provenance fields |
| `tests/test_gbif.py` | 9 | GBIF decisions (verified or review), cache, writing back |
| `tests/test_combine.py` | 7 | Merging datasets, conflicts, overlap |
| `tests/test_class_index.py` | 8 | Frozen class ids, detection of edited files and of new classes |
| `tests/test_provenance.py` | 15 | `dataset.json` rules, accepted license ids, commercial use |
| `tests/test_integrity.py` | 3 | Hashing, detection of changed and missing files |
| `tests/test_report.py` | 9 | Dataset report, final-version checks, id columns |
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
[datasets/README.md](../datasets/README.md) for the layout) and the file
`datasets/<name>/dataset.json` with the license and provenance of the dataset (section 10).

```bash
python scripts/build_interim.py swedish_leaf
python scripts/build_interim.py flavia
```

Expected for the complete datasets used when writing this guide:

```text
1125 images written to datasets\swedish_leaf\interim\images.csv
Taxonomy: 7 families, 10 genera, 11 species
  Acer: 75
  Alnus incana: 75
  ...
NOTE: no SHA-256 was computed. Final dataset versions require it: rerun with --hash.
WARNING: 1 of 15 mapping entries are not verified yet.
```

Swedish Leaf has 15 classes of 75 images, and Flavia gives `1907 images`. Open `datasets/<name>/interim/images.csv` to inspect the rows.

How to read the output:

- **"Classes in the mapping without images"** appears only when part of a dataset is missing
  from your `raw/` folder (for example if only some Swedish Leaf archives were downloaded). It is
  not an error, but the combined numbers will be lower than the ones in this guide.
- **`WARNING: N mapping entries are not verified yet`** means some entries are not
  `verified` (section 7).
- **`problems.txt`** (in `interim/`) lists files that could not be labelled, such as an
  unexpected file name. An empty or missing file is good.
- **`ERROR: ... does not exist`** means the `raw/` folder is missing or in the wrong place.

Optional flags: `--hash` computes the SHA-256 of every image and `--size` reads width and
height (needs Pillow, installed with `[dev]`). Both are slower. Without `--hash` the command ends
with `NOTE: no SHA-256 was computed`: that is fine for exploring, but a final version needs the
hashes (section 8.3).

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

Merges the tables of several datasets into one harmonised dataset with one taxonomy, reports
contradictions between datasets and writes a report. Run section 6 for each dataset first. The result
is *derived* from its sources: the images and original labels keep the licenses of their sources.

```bash
python scripts/build_combined.py swedish_leaf flavia
```

Expected for the complete datasets:

```text
3032 images from 2 datasets written to datasets\combined
Taxonomy: 25 families, 37 genera, 43 species
Taxa present in more than one dataset: 0
Genera present in more than one dataset: 2
  Acer: flavia=109, swedish_leaf=75
  Populus: flavia=64, swedish_leaf=150
Report: datasets\combined\report.md
```

Outputs in `datasets/combined/`:

- `images.csv`: all rows with the common columns.
- `taxonomy.csv`: one row per species or genus-only class. The columns `n_flavia` and
  `n_swedish_leaf` are the **number of images** of that row in each dataset.
- `report.md` and `report.json`: size, class distribution, items pending review, licenses, capture
  conditions, integrity and overlap (section 8.1).

Every column and field is defined in [data_formats.md](data_formats.md).

The overlap counts only the classes whose images are present locally; with an incomplete
download it is lower. The two datasets share no species, only the genera *Acer* and *Populus*.

Exit codes: `0` means no conflicts, `2` means taxonomy conflicts were found and printed as
`CONFLICT: ...` (for example the same species with two different families in two datasets),
`3` means `--release` found something missing (section 8.3), and `1` means a missing input such as
`ERROR: datasets\nope\interim\images.csv not found`.

### 8.1 Read the report

Open `datasets/combined/report.md`. Check these parts:

- **Class distribution:** the imbalance ratio (maximum / minimum images per class) and the classes
  below 20 images. For the local data the ratio is 1.54 and no class is small.
- **Pending review:** the original labels whose mapping is not `verified`. For the local data these
  are the four Flavia classes of the GBIF analysis plus *Sorbus intermedia* of Swedish Leaf
  (304 images).
- **Licenses:** all 3032 images are `LicenseRef-unspecified`, redistribution `unknown`, commercial
  use `no`.
- **Integrity:** images without hash (0 only if you ran `build_interim.py --hash`) and groups of
  identical files under different ids. The complete Swedish Leaf gives 3 such groups, described in
  [label_verification_analysis.md](label_verification_analysis.md).

The report has no timestamp, so running it twice on the same data gives the same file.

### 8.2 Freeze the class ids (`--version`)

Class ids are positions in an alphabetical list, so adding a class would shift the others. With
`--version` the first run writes `datasets/releases/<version>/class_index.json` and later runs check
the data against it. Use a throw-away version name to try it, and delete it afterwards, because a
real index must only be created when the taxonomy of that version is final:

```bash
python scripts/build_combined.py swedish_leaf --version demo
```

Expected: a line `Class index: created frozen index datasets\releases\demo\class_index.json (fingerprint ...)`.
`images.csv` and `taxonomy.csv` now also contain `family_id`, `genus_id` and `species_id`
(`species_id` is `-1` for a genus-only class such as *Acer* in Swedish Leaf).

Now try to add classes to the frozen version:

```bash
python scripts/build_combined.py swedish_leaf flavia --version demo
```

Expected, with exit code 1:

```text
ERROR: 77 classes are not in the frozen index datasets\releases\demo\class_index.json (for example family 'Adoxaceae'). A frozen version cannot change: use a new --version.
```

The count depends on your local files. If it does not stop, the protection is not working. Clean up:

```bash
rm -r datasets/releases/demo
```

(PowerShell: `Remove-Item -Recurse datasets\releases\demo`.)

### 8.3 Check that a build can be a final version (`--release`)

```bash
python scripts/build_interim.py swedish_leaf --hash
python scripts/build_interim.py flavia --hash
python scripts/build_combined.py swedish_leaf flavia --version demo --release
```

Expected with the current data, with exit code 3:

```text
NOT RELEASABLE: 3 groups of identical files under different image_id (for example swedish_leaf:l8nr016 and swedish_leaf:l8nr017)
NOT RELEASABLE: images whose label mapping is not verified (needs_review: 304)
```

This is the correct answer today: five names are still undecided and Swedish Leaf contains three
pairs of identical scans (see [label_verification_analysis.md](label_verification_analysis.md)). Without `--hash` you also get
`NOT RELEASABLE: N images without sha256 ...`. When every rule passes the last line is
`Release checks passed for version ...` and the exit code is 0. The rules are listed in
section 13 of [data_formats.md](data_formats.md). Remove the `demo` folder afterwards as in 8.2.

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

## 10. Provenance and license (`dataset.json`)

Each dataset has `datasets/<name>/dataset.json` with its license as a machine-readable identifier.
Load it:

```bash
python -c "from leaf_mlops.data.provenance import load_dataset_info; print(load_dataset_info('datasets/flavia/dataset.json'))"
```

It prints the fields (`license_id='LicenseRef-unspecified'`, `redistribution='unknown'`, ...).

**Try to break it** on a copy so the real file is not touched:

```bash
mkdir -p /tmp/check/flavia
sed 's/LicenseRef-unspecified/cc by something/' datasets/flavia/dataset.json > /tmp/check/flavia/dataset.json
python -c "import sys; from leaf_mlops.data.provenance import load_dataset_info; load_dataset_info(sys.argv[1])" /tmp/check/flavia/dataset.json
```

Expected: `ProvenanceError: ... license_id 'cc by something' is neither an accepted SPDX id nor
LicenseRef-...`. Free text is rejected on purpose. Changing `"redistribution": "unknown"` to
`"allowed"` while the license stays unspecified is also rejected. Delete the copy with
`rm -r /tmp/check`.

## 11. Integrity (SHA-256 hashes)

With the tables built with `--hash`, check that the raw images are exactly the ones that were hashed:

```bash
python scripts/build_interim.py swedish_leaf --hash
python scripts/build_interim.py flavia --hash
python scripts/build_combined.py swedish_leaf flavia
python scripts/verify_integrity.py datasets/combined/images.csv
```

Expected for the local copy:

```text
ok: 3032, changed: 0, missing: 0, without recorded hash: 0
```

Exit code 0 means every file matches. `changed` lists files whose content differs from the recorded
hash, `missing` files that no longer exist (both give exit code 2), and `without recorded hash` rows
that were built without `--hash`. To see a change detected without touching your data, the unit test
does it in a temporary folder:

```bash
python -m pytest tests/test_integrity.py -v
```

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `ModuleNotFoundError: leaf_mlops` | Environment not active, or package not installed | Activate `.venv`, run `pip install -e ".[dev]"` |
| `python -m pytest` collects 0 tests | Wrong folder | `cd` to the repository root |
| `ERROR: ... raw does not exist` | Dataset not downloaded | See `datasets/README.md` |
| `ERROR: GBIF request failed` | No internet or API down | Retry; if the cache exists, use it |
| `CONFLICT:` and exit code 2 | Datasets disagree on a family or genus | Fix the mapping entries involved |
| `NOT RELEASABLE:` and exit code 3 | A rule for final versions failed | Read the line: usually hashes (`--hash`) or unverified labels |
| `classes are not in the frozen index` | The data has a class the version did not have | Use a new `--version`; never edit the frozen file |
| `ProvenanceError` | `dataset.json` missing a field or with a free-text license | Fix the file following section 10 |
| PowerShell refuses to activate `.venv` | Execution policy | `Set-ExecutionPolicy -Scope Process RemoteSigned` |
