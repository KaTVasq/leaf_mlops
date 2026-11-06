import json

import pytest

from leaf_mlops.data.provenance import (
    ProvenanceError,
    commercial_use_allowed,
    is_valid_license_id,
    load_dataset_info,
    provenance_problems,
)


def write_info(tmp_path, name="demo", **overrides):
    data = {"name": name, "source_version": "2015", "source_url": "https://example.org",
            "license_id": "CC-BY-4.0", "redistribution": "allowed", "attribution": "Author (2015)",
            "capture_type": "field", "background": "natural"}
    data.update(overrides)
    folder = tmp_path / name
    folder.mkdir(exist_ok=True)
    path = folder / "dataset.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_valid_info_is_loaded(tmp_path):
    info = load_dataset_info(write_info(tmp_path))
    assert info.license_id == "CC-BY-4.0" and info.source_version == "2015"


@pytest.mark.parametrize("license_id", ["CC-BY-4.0", "CC0-1.0", "LicenseRef-unspecified", "LicenseRef-Kew-2020"])
def test_accepted_license_ids(license_id):
    assert is_valid_license_id(license_id)


@pytest.mark.parametrize("license_id", ["", "cc by 4.0", "unspecified; cite Wu et al. 2007", "GPL"])
def test_free_text_licenses_are_rejected(license_id):
    assert not is_valid_license_id(license_id)


def test_unspecified_license_cannot_allow_redistribution(tmp_path):
    path = write_info(tmp_path, license_id="LicenseRef-unspecified", redistribution="allowed")
    with pytest.raises(ProvenanceError, match="unspecified"):
        load_dataset_info(path)


def test_missing_fields_and_wrong_name_are_rejected(tmp_path):
    with pytest.raises(ProvenanceError, match="attribution"):
        load_dataset_info(write_info(tmp_path, attribution=""))
    path = write_info(tmp_path, name="other")
    data = json.loads(path.read_text(encoding="utf-8"))
    data["name"] = "different"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ProvenanceError, match="does not match folder"):
        load_dataset_info(path)


def test_attribution_is_optional_only_for_cc0():
    assert provenance_problems("CC0-1.0", "allowed", "", "") == []
    assert provenance_problems("CC-BY-4.0", "allowed", "", "")


def test_invalid_redistribution_and_url():
    problems = provenance_problems("CC-BY-4.0", "maybe", "x", "ftp://example.org")
    assert len(problems) == 2


def test_commercial_use():
    assert commercial_use_allowed("CC-BY-4.0")
    assert not commercial_use_allowed("CC-BY-NC-4.0")
    assert not commercial_use_allowed("CC-BY-NC-SA-4.0")
    assert not commercial_use_allowed("LicenseRef-unspecified")


def test_the_datasets_in_the_repository_have_valid_info():
    from pathlib import Path

    for path in sorted(Path(__file__).parent.parent.glob("datasets/*/dataset.json")):
        load_dataset_info(path)
