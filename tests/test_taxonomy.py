import pytest

from leaf_mlops.data.taxonomy import (
    IGNORE_INDEX,
    Taxonomy,
    TaxonomyError,
    load_taxonomy_from_csv,
)


def build() -> Taxonomy:
    t = Taxonomy()
    t.add("Quercus robur", "Quercus", "Fagaceae")
    t.add("Quercus ilex", "Quercus", "Fagaceae")
    t.add("Acer campestre", "Acer", "Sapindaceae")
    return t


def test_encode_is_deterministic():
    assert build().encode("Quercus robur") == {"family": 0, "genus": 1, "species": 2}


def test_contradictory_genus_is_rejected():
    t = build()
    with pytest.raises(TaxonomyError):
        t.add("Quercus robur", "Acer", "Sapindaceae")


def test_consistency_check():
    t = build()
    assert t.is_consistent("Fagaceae", "Quercus", "Quercus ilex")
    assert not t.is_consistent("Sapindaceae", "Quercus", "Quercus ilex")


def test_load_from_csv(tmp_path):
    csv_file = tmp_path / "tax.csv"
    csv_file.write_text("family,genus,species\nFagaceae,Quercus,Quercus robur\n", encoding="utf-8")
    assert load_taxonomy_from_csv(csv_file).classes("species") == ["Quercus robur"]


def test_genus_only_class_has_ignored_species_label():
    t = build()
    t.add_genus("Tilia", "Malvaceae")
    labels = t.encode_label("Tilia")
    assert labels["species"] == IGNORE_INDEX
    assert labels["genus"] == t.classes("genus").index("Tilia")


def test_genus_with_two_families_is_rejected():
    t = build()
    with pytest.raises(TaxonomyError):
        t.add_genus("Quercus", "Rosaceae")


def test_csv_with_empty_species_registers_the_genus(tmp_path):
    csv_file = tmp_path / "tax.csv"
    csv_file.write_text("family,genus,species\nMalvaceae,Tilia,\n", encoding="utf-8")
    t = load_taxonomy_from_csv(csv_file)
    assert t.classes("genus") == ["Tilia"] and t.classes("species") == []
