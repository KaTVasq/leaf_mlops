import json

import pytest

from leaf_mlops.data.mapping import MappingError, build_taxonomy, load_label_mapping
from leaf_mlops.data.taxonomy import TaxonomyError


def write(tmp_path, classes):
    path = tmp_path / "mapping.json"
    path.write_text(json.dumps({"classes": classes}), encoding="utf-8")
    return path


def entry(**overrides):
    base = {"original": "Quercus", "family": "Fagaceae", "genus": "Quercus",
            "species": None, "status": "proposed_unverified"}
    base.update(overrides)
    return base


def test_valid_mapping_and_taxonomy(tmp_path):
    path = write(tmp_path, {"1": entry(), "2": entry(original="Quercus robur", species="Quercus robur")})
    entries = load_label_mapping(path)
    assert entries["1"].species is None
    taxonomy = build_taxonomy(entries)
    assert taxonomy.classes("species") == ["Quercus robur"]
    assert taxonomy.classes("genus") == ["Quercus"]


def test_unknown_status_is_rejected(tmp_path):
    with pytest.raises(MappingError):
        load_label_mapping(write(tmp_path, {"1": entry(status="ok")}))


def test_species_must_belong_to_genus(tmp_path):
    with pytest.raises(MappingError):
        load_label_mapping(write(tmp_path, {"1": entry(species="Acer rubrum")}))


def test_missing_family_is_rejected(tmp_path):
    with pytest.raises(MappingError):
        load_label_mapping(write(tmp_path, {"1": entry(family="")}))


def test_contradicting_families_are_detected(tmp_path):
    path = write(tmp_path, {"1": entry(), "2": entry(family="Rosaceae")})
    with pytest.raises(TaxonomyError):
        build_taxonomy(load_label_mapping(path))


def test_shipped_swedish_mapping_is_valid():
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "datasets" / "swedish_leaf" / "label_mapping.json"
    entries = load_label_mapping(path)
    taxonomy = build_taxonomy(entries)
    assert len(entries) == 15
    assert len(taxonomy.classes("genus")) == 10


def test_shipped_flavia_files_are_consistent():
    from pathlib import Path

    from leaf_mlops.data.readers import load_flavia_ranges

    base = Path(__file__).resolve().parents[1] / "datasets" / "flavia"
    entries = load_label_mapping(base / "label_mapping.json")
    ranges = load_flavia_ranges(base / "label_ranges.csv")
    taxonomy = build_taxonomy(entries)

    assert len(entries) == 32
    assert {key for _, _, key in ranges} == set(entries)           # every class has a range
    assert sum(last - first + 1 for first, last, _ in ranges) == 1907  # published dataset size
    assert len(taxonomy.classes("species")) == 32
