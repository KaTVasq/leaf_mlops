from leaf_mlops.data.combine import combine, write_combined
from leaf_mlops.data.schema import FIELDS


def row(dataset, number, family, genus, species):
    base = {name: "" for name in FIELDS}
    base.update(image_id=f"{dataset}:{number}", source_dataset=dataset, source_image_id=str(number),
                family=family, genus=genus, species=species)
    return base


def test_combines_and_reports_shared_species():
    result = combine({
        "a": [row("a", 1, "Ulmaceae", "Ulmus", "Ulmus glabra"), row("a", 2, "Fagaceae", "Quercus", "")],
        "b": [row("b", 1, "Ulmaceae", "Ulmus", "Ulmus glabra")],
    })
    assert result.conflicts == []
    assert len(result.rows) == 3
    assert result.shared_taxa() == {"Ulmus glabra": {"a": 1, "b": 1}}
    assert result.taxonomy.classes("genus") == ["Quercus", "Ulmus"]


def test_contradicting_family_is_reported_and_row_skipped():
    result = combine({
        "a": [row("a", 1, "Ulmaceae", "Ulmus", "Ulmus glabra")],
        "b": [row("b", 1, "Cannabaceae", "Ulmus", "Ulmus glabra")],
    })
    assert len(result.rows) == 1
    assert any("b:1" in c for c in result.conflicts)


def test_spelling_variants_of_one_taxon_are_reported():
    result = combine({
        "a": [row("a", 1, "Ulmaceae", "Ulmus", "Ulmus glabra")],
        "b": [row("b", 1, "Ulmaceae", "Ulmus", "Ulmus  Glabra")],
    })
    assert any("written differently" in c for c in result.conflicts)


def test_duplicate_image_ids_are_reported():
    same = row("a", 1, "Ulmaceae", "Ulmus", "Ulmus glabra")
    result = combine({"a": [same, dict(same)]})
    assert len(result.rows) == 1
    assert any("duplicate image_id" in c for c in result.conflicts)


def test_write_combined_outputs_images_and_taxonomy(tmp_path):
    result = combine({
        "a": [row("a", 1, "Ulmaceae", "Ulmus", "Ulmus glabra"), row("a", 2, "Fagaceae", "Quercus", "")],
        "b": [row("b", 1, "Ulmaceae", "Ulmus", "Ulmus glabra")],
    })
    write_combined(result, tmp_path)
    taxonomy = (tmp_path / "taxonomy.csv").read_text(encoding="utf-8").splitlines()
    assert taxonomy[0] == "family,genus,species,n_a,n_b"
    assert "Fagaceae,Quercus,,1,0" in taxonomy
    assert "Ulmaceae,Ulmus,Ulmus glabra,1,1" in taxonomy
    assert len((tmp_path / "images.csv").read_text(encoding="utf-8").splitlines()) == 4


def test_genus_overlap_includes_genus_only_classes():
    result = combine({
        "a": [row("a", 1, "Sapindaceae", "Acer", "")],
        "b": [row("b", 1, "Sapindaceae", "Acer", "Acer rubrum"), row("b", 2, "Sapindaceae", "Acer", "Acer pictum")],
    })
    assert result.shared_taxa() == {}
    assert result.shared_genera() == {"Acer": {"a": 1, "b": 2}}


def test_taxonomy_csv_keeps_genus_only_class_of_a_genus_with_species(tmp_path):
    result = combine({
        "a": [row("a", 1, "Sapindaceae", "Acer", "")],
        "b": [row("b", 1, "Sapindaceae", "Acer", "Acer rubrum")],
    })
    write_combined(result, tmp_path)
    lines = (tmp_path / "taxonomy.csv").read_text(encoding="utf-8").splitlines()
    assert "Sapindaceae,Acer,,1,0" in lines
    assert "Sapindaceae,Acer,Acer rubrum,0,1" in lines
    # every image is counted exactly once
    assert sum(int(x) for line in lines[1:] for x in line.split(",")[3:]) == 2
