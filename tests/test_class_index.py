import json

import pytest

from leaf_mlops.data.class_index import ClassIndex, ClassIndexError
from leaf_mlops.data.taxonomy import IGNORE_INDEX, Taxonomy


def make_taxonomy(*species):
    taxonomy = Taxonomy()
    for name, genus, family in species:
        taxonomy.add(name, genus, family)
    return taxonomy


BASE = (("Ulmus glabra", "Ulmus", "Ulmaceae"), ("Acer rubrum", "Acer", "Sapindaceae"))


def test_ids_follow_alphabetical_order_and_match_taxonomy_encode():
    taxonomy = make_taxonomy(*BASE)
    index = ClassIndex.from_taxonomy(taxonomy, "v1")
    assert index.encode("Ulmaceae", "Ulmus", "Ulmus glabra") == taxonomy.encode("Ulmus glabra")


def test_unknown_species_gets_ignore_index():
    index = ClassIndex.from_taxonomy(make_taxonomy(*BASE), "v1")
    assert index.encode("Sapindaceae", "Acer", "")["species"] == IGNORE_INDEX


def test_save_and_load_round_trip(tmp_path):
    index = ClassIndex.from_taxonomy(make_taxonomy(*BASE), "v1")
    path = tmp_path / "v1" / "class_index.json"
    index.save(path)
    loaded = ClassIndex.load(path)
    assert loaded == index and loaded.fingerprint == index.fingerprint


def test_frozen_ids_do_not_move_when_a_class_is_added():
    before = ClassIndex.from_taxonomy(make_taxonomy(*BASE), "v1")
    bigger = make_taxonomy(*BASE, ("Abies alba", "Abies", "Pinaceae"))
    # a naive re-encoding would shift every id because "Abies" sorts first
    shifted = Taxonomy.encode(bigger, "Ulmus glabra")["genus"]
    assert shifted != before.encode("Ulmaceae", "Ulmus", "Ulmus glabra")["genus"]
    assert before.missing_from(bigger) == ["family 'Pinaceae'", "genus 'Abies'", "species 'Abies alba'"]
    assert before.missing_from(make_taxonomy(*BASE)) == []


def test_classes_without_data_keep_their_reserved_id():
    index = ClassIndex.from_taxonomy(make_taxonomy(*BASE), "v1")
    partial = make_taxonomy(BASE[0])
    assert "species 'Acer rubrum'" in index.unused_in(partial)
    assert index.id_of("species", "Acer rubrum") == 0


def test_editing_the_file_is_detected(tmp_path):
    path = tmp_path / "class_index.json"
    ClassIndex.from_taxonomy(make_taxonomy(*BASE), "v1").save(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["levels"]["genus"] = {"Ulmus": 0, "Acer": 1}  # swapped ids, fingerprint not updated
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ClassIndexError, match="fingerprint"):
        ClassIndex.load(path)


def test_ids_with_gaps_are_rejected(tmp_path):
    path = tmp_path / "class_index.json"
    ClassIndex.from_taxonomy(make_taxonomy(*BASE), "v1").save(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["levels"]["family"] = {"Sapindaceae": 0, "Ulmaceae": 5}
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ClassIndexError, match="without gaps"):
        ClassIndex.load(path)


def test_version_is_required_and_unknown_class_raises():
    with pytest.raises(ClassIndexError):
        ClassIndex.from_taxonomy(make_taxonomy(*BASE), " ")
    index = ClassIndex.from_taxonomy(make_taxonomy(*BASE), "v1")
    with pytest.raises(ClassIndexError):
        index.encode("Ulmaceae", "Ulmus", "Ulmus minor")
