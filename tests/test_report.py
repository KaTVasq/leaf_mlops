import csv

from leaf_mlops.data.class_index import ClassIndex
from leaf_mlops.data.combine import combine, write_combined
from leaf_mlops.data.report import build_report, release_problems, render_markdown, write_report
from leaf_mlops.data.schema import FIELDS


def row(dataset, number, family, genus, species, **overrides):
    base = {name: "" for name in FIELDS}
    base.update(
        image_id=f"{dataset}:{number}", source_dataset=dataset, source_image_id=str(number),
        family=family, genus=genus, species=species, original_label=species or genus,
        mapping_status="verified", organ="leaf", capture_type="scan", background="plain",
        width="100", height="100", sha256=f"{dataset}{number:060d}"[:64],
        source_version="2015", source_url="https://example.org", license_id="CC-BY-4.0",
        redistribution="allowed", attribution="Author (2015)",
    )
    base.update(overrides)
    return base


def build(**extra):
    tables = {
        "a": [row("a", 1, "Ulmaceae", "Ulmus", "Ulmus glabra"), row("a", 2, "Ulmaceae", "Ulmus", "Ulmus glabra"),
              row("a", 3, "Sapindaceae", "Acer", "")],
        "b": [row("b", 1, "Ulmaceae", "Ulmus", "Ulmus glabra", license_id="CC-BY-NC-4.0")],
    }
    tables.update(extra)
    return combine(tables)


def test_report_totals_and_distribution():
    report = build_report(build(), small_class_threshold=2)
    assert report["totals"] == {"images": 4, "datasets": 2, "families": 2, "genera": 2,
                                "species": 1, "genus_only_classes": 1}
    assert report["per_dataset"] == {"a": {"images": 3, "classes": 2}, "b": {"images": 1, "classes": 1}}
    dist = report["class_distribution"]
    assert (dist["min_images"], dist["max_images"], dist["imbalance_ratio"]) == (1, 3, 3.0)
    assert dist["small_classes"] == [{"name": "Acer", "images": 1}]
    assert report["overlap"]["shared_genera"] == {"Ulmus": {"a": 2, "b": 1}}


def test_report_lists_pending_review_and_license_breakdown():
    tables = {"c": [row("c", 1, "Lauraceae", "Machilus", "Machilus nanmu", mapping_status="needs_review",
                        original_label="Phoebe nanmu")]}
    report = build_report(build(**tables))
    assert report["pending_review"] == [
        {"dataset": "c", "original_label": "Phoebe nanmu", "status": "needs_review", "images": 1}]
    by_license = {x["license_id"]: x for x in report["licenses"]}
    assert by_license["CC-BY-NC-4.0"]["commercial_use"] is False
    assert by_license["CC-BY-4.0"]["images"] == 4


def test_report_is_deterministic_and_written(tmp_path):
    result = build()
    first = render_markdown(build_report(result))
    assert first == render_markdown(build_report(build()))
    write_report(build_report(result), tmp_path)
    assert (tmp_path / "report.json").is_file()
    text = (tmp_path / "report.md").read_text(encoding="utf-8")
    for heading in ("## Size", "## Class distribution", "## Pending review", "## Licenses",
                    "## Integrity", "## Overlap between datasets", "## Conflicts"):
        assert heading in text


def test_release_accepts_a_complete_build():
    result = build()
    index = ClassIndex.from_taxonomy(result.taxonomy, "v1")
    assert release_problems(result, index) == []


def test_release_requires_index_hash_and_verified_labels():
    result = build(c=[row("c", 1, "Lauraceae", "Machilus", "Machilus nanmu", sha256="",
                          mapping_status="needs_review")])
    problems = release_problems(result, None)
    text = " | ".join(problems)
    assert "no frozen class index" in text
    assert "1 images without sha256" in text
    assert "not verified (needs_review: 1)" in text


def test_release_rejects_duplicate_files_and_free_text_license():
    same = "f" * 64
    result = combine({
        "a": [row("a", 1, "Ulmaceae", "Ulmus", "Ulmus glabra", sha256=same)],
        "b": [row("b", 1, "Ulmaceae", "Ulmus", "Ulmus glabra", sha256=same,
                  license_id="unspecified; cite Wu et al. 2007")],
    })
    index = ClassIndex.from_taxonomy(result.taxonomy, "v1")
    text = " | ".join(release_problems(result, index))
    assert "identical files" in text
    assert "neither an accepted SPDX id" in text


def test_release_rejects_conflicts_and_empty_datasets():
    conflicting = combine({
        "a": [row("a", 1, "Ulmaceae", "Ulmus", "Ulmus glabra")],
        "b": [row("b", 1, "Cannabaceae", "Ulmus", "Ulmus glabra")],
    })
    assert any("conflicts" in p for p in release_problems(conflicting, None))
    assert release_problems(combine({"a": []}), None) == ["the dataset has no images"]


def test_ids_are_written_with_a_frozen_index(tmp_path):
    result = build()
    index = ClassIndex.from_taxonomy(result.taxonomy, "v1")
    write_combined(result, tmp_path, index)

    images = list(csv.DictReader(open(tmp_path / "images.csv", encoding="utf-8")))
    acer = next(r for r in images if r["genus"] == "Acer")
    assert acer["species_id"] == "-1" and acer["genus_id"] == "0" and acer["family_id"] == "0"
    ulmus = next(r for r in images if r["species"] == "Ulmus glabra")
    assert (ulmus["family_id"], ulmus["genus_id"], ulmus["species_id"]) == ("1", "1", "0")

    taxonomy = (tmp_path / "taxonomy.csv").read_text(encoding="utf-8").splitlines()
    assert taxonomy[0] == "family,genus,species,family_id,genus_id,species_id,n_a,n_b"
    assert "Sapindaceae,Acer,,0,0,-1,1,0" in taxonomy
    assert "Ulmaceae,Ulmus,Ulmus glabra,1,1,0,2,1" in taxonomy


def test_without_an_index_no_id_columns_are_written(tmp_path):
    write_combined(build(), tmp_path)
    header = (tmp_path / "images.csv").read_text(encoding="utf-8").splitlines()[0]
    assert "species_id" not in header
