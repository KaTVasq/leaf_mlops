import pytest

from leaf_mlops.data.mapping import LabelEntry, MappingError
from leaf_mlops.data.readers import load_flavia_ranges, read_flavia, read_swedish_leaf
from leaf_mlops.data.schema import FIELDS, write_records_csv


def make_entry(key, species, genus="Ulmus", family="Ulmaceae"):
    return LabelEntry(key=key, original=species or genus, family=family, genus=genus,
                      species=species, status="proposed_unverified")


def touch(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"")


def test_swedish_reader(tmp_path):
    raw = tmp_path / "raw"
    touch(raw / "leaf1" / "l1nr002.tif")
    touch(raw / "leaf1" / "l1nr001.tif")
    touch(raw / "leaf2" / "L2NR001.TIF")          # upper case must work
    touch(raw / "leaf9" / "l9nr001.tif")          # class not in mapping
    touch(raw / "leaf1" / "notes.txt")            # ignored
    touch(raw / "leaf1" / "weird.tif")            # unexpected name
    mapping = {"1": make_entry("1", "Ulmus glabra"), "2": make_entry("2", None, "Quercus", "Fagaceae")}

    records, problems = read_swedish_leaf(raw, mapping)

    assert [r.source_image_id for r in records] == ["l1nr001", "l1nr002", "l2nr001"]
    assert records[0].file_path == "leaf1/l1nr001.tif"
    assert records[0].species == "Ulmus glabra"
    assert records[2].species == "" and records[2].genus == "Quercus"
    assert len(problems) == 2
    assert records[0].image_id == "swedish_leaf:l1nr001"


def test_flavia_reader_and_ranges(tmp_path):
    raw = tmp_path / "raw"
    for name in ("1001", "1002", "1060", "9999"):
        touch(raw / "Leaves" / f"{name}.jpg")
    touch(raw / "Leaves" / "abc.jpg")
    table = tmp_path / "ranges.csv"
    table.write_text("first_id,last_id,key\n1060,1100,b\n1001,1059,a\n", encoding="utf-8")
    mapping = {"a": make_entry("a", "Ulmus glabra"), "b": make_entry("b", "Ulmus minor")}

    records, problems = read_flavia(raw, load_flavia_ranges(table), mapping)

    assert [(r.source_image_id, r.species) for r in records] == [
        ("1001", "Ulmus glabra"), ("1002", "Ulmus glabra"), ("1060", "Ulmus minor")]
    assert len(problems) == 2


def test_overlapping_ranges_are_rejected(tmp_path):
    table = tmp_path / "ranges.csv"
    table.write_text("first_id,last_id,key\n1,10,a\n10,20,b\n", encoding="utf-8")
    with pytest.raises(MappingError):
        load_flavia_ranges(table)


def test_empty_range_table_is_rejected(tmp_path):
    with pytest.raises(MappingError):
        read_flavia(tmp_path, [], {})


def test_csv_output_has_every_field(tmp_path):
    raw = tmp_path / "raw"
    touch(raw / "l1nr001.tif")
    records, _ = read_swedish_leaf(raw, {"1": make_entry("1", "Ulmus glabra")}, compute_hash=True)
    out = tmp_path / "interim" / "images.csv"
    write_records_csv(records, out)
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[0].split(",") == list(FIELDS)
    assert len(lines) == 2
    assert "e3b0c44298fc1c149afbf4c8996fb924" in lines[1]  # SHA-256 of an empty file
