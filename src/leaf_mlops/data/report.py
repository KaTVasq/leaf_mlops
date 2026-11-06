"""Report on a harmonised (combined) dataset, and the checks a final version must pass.

The report answers, before anyone trains on the data: how big is it, how are the classes
distributed, what is still pending review, under which licenses can it be used and is it
traceable (hashes). It is deterministic: the same input gives the same report, so it can be
committed and compared between versions.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median

from leaf_mlops.data.class_index import ClassIndex
from leaf_mlops.data.combine import CombinedDataset
from leaf_mlops.data.provenance import commercial_use_allowed, provenance_problems

SMALL_CLASS_THRESHOLD = 20


def _class_table(result: CombinedDataset) -> list[dict]:
    """One entry per class of the unified taxonomy (species, or genus-only class)."""
    taxonomy = result.taxonomy
    table = []
    for name, per_dataset in result.counts.items():
        if name in taxonomy.species_to_genus:
            genus, kind = taxonomy.species_to_genus[name], "species"
        else:
            genus, kind = name, "genus_only"
        table.append({
            "name": name,
            "kind": kind,
            "genus": genus,
            "family": taxonomy.genus_to_family[genus],
            "images": sum(per_dataset.values()),
            "per_dataset": dict(sorted(per_dataset.items())),
        })
    return sorted(table, key=lambda c: (c["family"], c["genus"], c["kind"] != "genus_only", c["name"]))


def _duplicate_hashes(rows: list[dict[str, str]]) -> list[list[str]]:
    by_hash: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        if row.get("sha256"):
            by_hash[row["sha256"]].append(row["image_id"])
    return sorted(sorted(ids) for ids in by_hash.values() if len(ids) > 1)


def build_report(
    result: CombinedDataset,
    index: ClassIndex | None = None,
    small_class_threshold: int = SMALL_CLASS_THRESHOLD,
) -> dict:
    rows, taxonomy = result.rows, result.taxonomy
    classes = _class_table(result)
    sizes = [c["images"] for c in classes]

    per_dataset: dict[str, dict[str, int]] = {}
    for dataset in sorted({row["source_dataset"] for row in rows}):
        per_dataset[dataset] = {
            "images": sum(1 for r in rows if r["source_dataset"] == dataset),
            "classes": sum(1 for c in classes if dataset in c["per_dataset"]),
        }

    pending = Counter(
        (r["source_dataset"], r["original_label"], r["mapping_status"])
        for r in rows if r["mapping_status"] != "verified"
    )
    licenses = Counter((r["license_id"], r["redistribution"]) for r in rows)
    capture = Counter((r["source_dataset"], r["capture_type"], r["background"]) for r in rows)

    return {
        "version": index.version if index else "",
        "totals": {
            "images": len(rows),
            "datasets": len(per_dataset),
            "families": len(taxonomy.classes("family")),
            "genera": len(taxonomy.classes("genus")),
            "species": len(taxonomy.classes("species")),
            "genus_only_classes": sum(1 for c in classes if c["kind"] == "genus_only"),
        },
        "per_dataset": per_dataset,
        "class_distribution": {
            "classes": len(classes),
            "min_images": min(sizes, default=0),
            "median_images": median(sizes) if sizes else 0,
            "max_images": max(sizes, default=0),
            "imbalance_ratio": round(max(sizes) / min(sizes), 2) if sizes and min(sizes) else None,
            "small_class_threshold": small_class_threshold,
            "small_classes": [
                {"name": c["name"], "images": c["images"]} for c in classes if c["images"] < small_class_threshold
            ],
            "classes_detail": classes,
        },
        "mapping_status": dict(sorted(Counter(r["mapping_status"] for r in rows).items())),
        "pending_review": [
            {"dataset": d, "original_label": label, "status": status, "images": n}
            for (d, label, status), n in sorted(pending.items())
        ],
        "licenses": [
            {"license_id": lic, "redistribution": red, "images": n,
             "commercial_use": commercial_use_allowed(lic)}
            for (lic, red), n in sorted(licenses.items())
        ],
        "capture": [
            {"dataset": d, "capture_type": c, "background": b, "images": n}
            for (d, c, b), n in sorted(capture.items())
        ],
        "integrity": {
            "images_without_sha256": sum(1 for r in rows if not r["sha256"]),
            "images_without_size": sum(1 for r in rows if not (r["width"] and r["height"])),
            "duplicate_hash_groups": _duplicate_hashes(rows),
        },
        "overlap": {
            "shared_species_or_genus_only": result.shared_taxa(),
            "shared_genera": result.shared_genera(),
        },
        "class_index": {
            "version": index.version,
            "fingerprint": index.fingerprint,
            "reserved_without_images": index.unused_in(taxonomy),
        } if index else None,
        "conflicts": list(result.conflicts),
    }


def release_problems(result: CombinedDataset, index: ClassIndex | None) -> list[str]:
    """Reasons why this build is not acceptable as a final dataset version (empty list = acceptable)."""
    rows = result.rows
    problems: list[str] = []
    if not rows:
        return ["the dataset has no images"]
    if index is None:
        problems.append("no frozen class index: pass --index so class ids are fixed for this version")
    if result.conflicts:
        problems.append(f"{len(result.conflicts)} conflicts (taxonomy or identifiers); see the report")
    missing_hash = sum(1 for r in rows if not r["sha256"])
    if missing_hash:
        problems.append(f"{missing_hash} images without sha256: rerun build_interim.py with --hash")
    duplicates = _duplicate_hashes(rows)
    if duplicates:
        problems.append(f"{len(duplicates)} groups of identical files under different image_id "
                        f"(for example {duplicates[0][0]} and {duplicates[0][1]})")
    unverified = Counter(r["mapping_status"] for r in rows if r["mapping_status"] != "verified")
    if unverified:
        detail = ", ".join(f"{status or 'empty'}: {n}" for status, n in sorted(unverified.items()))
        problems.append(f"images whose label mapping is not verified ({detail})")
    seen = {(r["license_id"], r["redistribution"], r["attribution"], r["source_url"]) for r in rows}
    for license_id, redistribution, attribution, source_url in sorted(seen):
        for problem in provenance_problems(license_id, redistribution, attribution, source_url):
            problems.append(f"provenance of {license_id or 'empty license'}: {problem}")
    return problems


def render_markdown(report: dict) -> str:
    totals, dist = report["totals"], report["class_distribution"]
    title = f"# Dataset report {report['version']}".rstrip()
    lines = [title, "", "## Size", "",
             "| Images | Datasets | Families | Genera | Species | Genus-only classes |",
             "| --- | --- | --- | --- | --- | --- |",
             f"| {totals['images']} | {totals['datasets']} | {totals['families']} | {totals['genera']} "
             f"| {totals['species']} | {totals['genus_only_classes']} |", "",
             "| Dataset | Images | Classes |", "| --- | --- | --- |"]
    lines += [f"| {d} | {v['images']} | {v['classes']} |" for d, v in report["per_dataset"].items()]

    lines += ["", "## Class distribution", "",
              f"{dist['classes']} classes; images per class: min {dist['min_images']}, "
              f"median {dist['median_images']}, max {dist['max_images']}; "
              f"imbalance ratio (max/min) {dist['imbalance_ratio']}.", ""]
    if dist["small_classes"]:
        small = ", ".join(f"{c['name']} ({c['images']})" for c in dist["small_classes"])
        lines.append(f"Classes with fewer than {dist['small_class_threshold']} images: {small}.")
    else:
        lines.append(f"No class has fewer than {dist['small_class_threshold']} images.")
    datasets = list(report["per_dataset"])
    lines += ["", "| Family | Genus | Class | Kind | Images | " + " | ".join(datasets) + " |",
              "| --- | --- | --- | --- | --- | " + " | ".join("---" for _ in datasets) + " |"]
    for c in dist["classes_detail"]:
        per = " | ".join(str(c["per_dataset"].get(d, 0)) for d in datasets)
        lines.append(f"| {c['family']} | {c['genus']} | {c['name']} | {c['kind']} | {c['images']} | {per} |")

    status_text = ", ".join(f"{k or 'empty'} {v}" for k, v in report["mapping_status"].items())
    lines += ["", "## Pending review", "",
              "Images by mapping status: " + (status_text or "none") + ".", ""]
    if report["pending_review"]:
        lines += ["| Dataset | Original label | Status | Images |", "| --- | --- | --- | --- |"]
        lines += [f"| {p['dataset']} | {p['original_label']} | {p['status']} | {p['images']} |"
                  for p in report["pending_review"]]
    else:
        lines.append("Nothing is pending review.")

    lines += ["", "## Licenses", "",
              "| License | Redistribution | Commercial use | Images |", "| --- | --- | --- | --- |"]
    for x in report["licenses"]:
        commercial = "yes" if x["commercial_use"] else "no"
        lines.append(f"| {x['license_id']} | {x['redistribution']} | {commercial} | {x['images']} |")

    lines += ["", "## Capture conditions", "",
              "| Dataset | Capture type | Background | Images |", "| --- | --- | --- | --- |"]
    lines += [f"| {x['dataset']} | {x['capture_type']} | {x['background']} | {x['images']} |"
              for x in report["capture"]]

    integrity = report["integrity"]
    lines += ["", "## Integrity", "",
              f"- Images without SHA-256: {integrity['images_without_sha256']}",
              f"- Images without width and height: {integrity['images_without_size']}",
              f"- Groups of identical files under different ids: {len(integrity['duplicate_hash_groups'])}"]

    overlap = report["overlap"]
    lines += ["", "## Overlap between datasets", ""]
    kinds = (("Species or genus-only classes", "shared_species_or_genus_only"), ("Genera", "shared_genera"))
    for label, key in kinds:
        shared = overlap[key]
        lines.append(f"- {label} present in more than one dataset: {len(shared)}"
                     + ("".join(f"\n  - {n}: " + ", ".join(f"{d} {c}" for d, c in per.items())
                                for n, per in shared.items())))

    if report["class_index"]:
        ci = report["class_index"]
        lines += ["", "## Class index", "",
                  f"- Version: {ci['version']}", f"- Fingerprint: `{ci['fingerprint']}`",
                  "- Classes reserved in the index but without images in this build: "
                  f"{len(ci['reserved_without_images'])}"]
    else:
        lines += ["", "## Class index", "", "No frozen class index: class ids are not fixed."]

    lines += ["", "## Conflicts", ""]
    lines += [f"- {c}" for c in report["conflicts"]] or ["None."]
    return "\n".join(lines) + "\n"


def write_report(report: dict, out_dir: str | Path) -> None:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (out_dir / "report.md").write_text(render_markdown(report), encoding="utf-8")
