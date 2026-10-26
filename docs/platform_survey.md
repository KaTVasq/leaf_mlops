# Platform architecture survey

Technology selection for the platform that creates, annotates, versions and manages
tree-leaf image datasets. The choice is derived from the requirements in
[requirements.md](requirements.md) (IDs such as FR-08 or NFR-01 refer to that file).

- **Last updated:** 26/10/2026
- **Status:** the data layer (readers, label mapping, GBIF check, combined table, storage
  abstraction) is implemented and tested. The web application (Django) is **not built yet**;
  this document justifies that choice before it is.

## 1. Method

1. Collect requirements from the project proposal, the tutor's feedback and the team
   meetings ([requirements.md](requirements.md)).
2. Reduce them to the few **architectural drivers** that actually constrain technology
   (section 2).
3. For each component, list the realistic alternatives, compare them against the drivers
   and record the decision and what would make us revisit it (section 3).
4. Isolate the choices that carry the most risk behind an interface, so they can be changed
   without rewriting the application (section 4).

Comparisons are qualitative (meets / partly / does not meet) on purpose: the weights depend
on the requirements, and numeric scores would give a false sense of precision. Statements
about third-party tools are general descriptions to be confirmed with citations in the
report.

## 2. Architectural drivers

| Driver | Requirements | Consequence for the design |
| --- | --- | --- |
| A new user can run everything locally without accounts | NFR-01, NFR-05, NFR-07 | Defaults must work offline: local file system, a database that needs no server in development, no mandatory cloud service. |
| Storage must be replaceable | FR-12, NFR-03 | Application code talks to a small storage interface, never to a vendor SDK. |
| Data model is relational and evolves | FR-02, FR-04, FR-05, FR-07, FR-08 | Taxonomy (family, genus, species), images, annotation layers, dataset versions and their membership are linked records with constraints. |
| Corrections must be auditable | FR-13, FR-14, NFR-04 | Users, roles and a change history are needed from the start. |
| Datasets are reproducible releases | FR-08, FR-10, NFR-04, NFR-10 | A version is an immutable list of image ids plus recipe, exported in open formats. |
| One developer, limited time | NFR-06 | Prefer a framework that already provides authentication, permissions, migrations and an admin interface. |
| Raw data is licence-sensitive | NFR-02 | Raw images and databases are never committed; only code, mappings and reports are. |

## 3. Component analysis

### 3.1 Backend framework

| Option | Auth, roles, admin and migrations included | Fits a relational, review-oriented data model | Learning and maintenance cost | Verdict |
| --- | --- | --- | --- | --- |
| **Django** | Yes (FR-13, FR-14) | Yes: ORM with constraints and migrations | Medium, large ecosystem | **Selected** |
| FastAPI | No: must be assembled (ORM, migrations, auth, admin) | Yes, with extra libraries | Medium, more glue code | Good for a future inference service (FR-16), not for the core |
| Flask | No: same as FastAPI | Yes, with extra libraries | Low to start, high to complete | Rejected: reimplements what Django ships |
| Scripts and files only (no web app) | Not applicable | Partly: CSV/JSON only | Lowest | Kept as the base layer, but it cannot give review workflows or roles (FR-13, FR-14) |

The scripts-only layer is already implemented and is not wasted: Django will use the same
`leaf_mlops.data` package for ingestion and label mapping.

### 3.2 Database

| Option | Constraints and joins (taxonomy, versions) | Runs without a server in development (NFR-01) | Scale (NFR-03) | Verdict |
| --- | --- | --- | --- | --- |
| **PostgreSQL** | Yes | No, needs a server or container | Yes | **Selected for production** |
| SQLite | Yes, with limits on concurrent writes | **Yes** | Adequate for development and tests | **Selected for development and tests** |
| MongoDB | Weaker for relational integrity | No | Yes | Rejected: the model is relational |

Django supports both PostgreSQL and SQLite through configuration, so the database is chosen
with an environment variable (for example `DATABASE_URL`), exactly like storage. Features
that exist only in PostgreSQL must not be used in the core model.

### 3.3 Image storage

| Option | Needs an account or server | Fits development (NFR-01) | Fits production at scale (NFR-03) | Verdict |
| --- | --- | --- | --- | --- |
| **Local file system** | No | **Yes** | Limited by one disk | **Default** (`STORAGE_BACKEND=local`) |
| **S3-compatible API** (MinIO, Cloudflare R2, AWS S3) | Yes, or a MinIO container | Only with MinIO | **Yes** | **Optional** (`STORAGE_BACKEND=s3`) |
| Cloudflare R2 only | Cloudflare account, bucket and credentials | No | Yes | Rejected as a hard dependency: anyone cloning the repository would need an account |
| Database blobs | No | Yes | No | Rejected: bloats the database and backups |

Cloudflare R2 remains a valid production target because it speaks the S3 API, but it is a
deployment choice, not a dependency of the code. MinIO gives a free S3-compatible server for
testing the S3 path locally.

### 3.4 Annotation and review

| Option | Extra infrastructure | Fits FR-07 and FR-13 | Verdict |
| --- | --- | --- | --- |
| **Django admin plus custom views** | None | Review and correction of labels, with audit trail and roles | **Selected** for label review |
| Label Studio | Separate service and integration | Strong for general annotation tasks | Candidate to import and export annotations if needed |
| CVAT | Separate service and integration | Strong for polygons and masks | Not needed now: masks come from the segmentation TFG and are imported (see "Won't do" in the requirements) |

### 3.5 Dataset versioning

| Option | Traceability to image and mapping (NFR-04) | Extra tooling | Verdict |
| --- | --- | --- | --- |
| **Versions as records in the platform database** (recipe plus list of image ids, exported to open files) | Yes, native | None | **Selected** |
| DVC | Good for files tracked with Git | Extra tool and remote storage | Considered as a complement for the data files; does not model labels, taxonomy or review |
| lakeFS | Good for object stores | Separate server | Overkill for one developer |
| Hugging Face Hub or Zenodo | Publication, not management | Account | Reserved for **publishing** a finished release |

### 3.6 Frontend

| Option | Why |
| --- | --- |
| **Django templates with HTMX** (Tailwind optional) | Server-rendered pages with partial updates; no separate JavaScript application to build and maintain (NFR-06). Works on mobile browsers for later uploads (FR-15). |
| Single-page application (React or similar) | Rejected for now: a second codebase and API layer without a requirement that needs it. |

### 3.7 Species identification service (optional, FR-16)

A model served from the backend gives control over inference and keeps the academic goal;
the Pl@ntNet API would add a third-party dependency, usage limits and possible cost. It is
optional and will be built last, behind the same kind of interface as storage.

## 4. Isolating risk: configuration and interfaces

The two decisions most likely to change are storage and database. Both are selected by
environment variables and have a working default that needs nothing installed:

| Setting | Default | Alternatives |
| --- | --- | --- |
| `STORAGE_BACKEND` | `local` (`MEDIA_ROOT=./data/media`) | `s3` with `S3_BUCKET`, `S3_ENDPOINT_URL`, credentials |
| Database | SQLite | PostgreSQL (production) |

Storage is already implemented in `src/leaf_mlops/storage`. The application depends only on:

```python
storage.save(key, data)      # bytes or file object; returns the key
storage.open(key)            # binary file object
storage.exists(key)
storage.delete(key)
storage.list_keys(prefix)
```

Both backends pass the same test suite (`tests/test_storage.py`), and the S3 backend is
tested with an injected fake client, so no account is needed to run the tests. Keys are
validated to reject absolute paths and `..`, so a key cannot escape the storage root.

## 5. Resulting architecture

```text
 readers (per dataset) ──► common table ──► label mapping + GBIF check ──► combined dataset
                                                        │
 Django app (users, roles, review, versions) ◄──────────┘
        │                         │
        ▼                         ▼
 Database (SQLite / PostgreSQL)   Storage interface ──► local files | S3-compatible (MinIO, R2)
        │
        ▼
 Versioned exports (CSV or Parquet + images) for the other TFGs and external researchers
```

What exists today is the left half of the diagram (readers, mapping, GBIF verification,
combined table and storage). The Django application, database models, review workflow and
versioned export are the next stage.

## 6. Risks and open points

| Risk | Mitigation |
| --- | --- | 
| Cloud vendor lock-in | Storage interface with a local default (section 4). |
| Licences prevent redistributing images | Only mappings, reports and code are versioned; images are fetched from the original source (NFR-02). |
| Scope grows beyond one TFG | Requirements are prioritised; "Could" items (upload, inference) are built last. |
| Annotation layers from other TFGs arrive in different formats | Agree an exchange format early (requirements, open decision 4). |
| PostgreSQL-only features creep into the model | Run the test suite on SQLite and on PostgreSQL in CI once the Django app exists. |
