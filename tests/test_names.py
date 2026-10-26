from leaf_mlops.data.names import normalize_key, parse_name, suggest_names


def test_case_and_underscores_are_normalized():
    assert parse_name("quercus_ROBUR").canonical == "Quercus robur"


def test_quoted_cultivar_is_separated():
    parsed = parse_name("Salix alba 'Sericea'")
    assert parsed.canonical == "Salix alba"
    assert parsed.cultivar == "Sericea"


def test_genus_only_name():
    parsed = parse_name("Quercus")
    assert parsed.canonical == "Quercus" and parsed.epithet is None


def test_hybrid_sign_is_detected():
    parsed = parse_name("Populus x canadensis")
    assert parsed.is_hybrid and parsed.canonical == "Populus canadensis"


def test_variety_goes_to_infraspecific():
    assert parse_name("Salix alba var. vitellina").infraspecific == "var. vitellina"


def test_empty_name():
    assert parse_name("   ").canonical == ""


def test_key_ignores_case_hyphen_underscore_and_accents():
    assert normalize_key("Anhui-Barberry") == normalize_key("anhui_barberry")
    assert normalize_key("Acer  Campéstre") == "acer campestre"


def test_typo_suggestions():
    reference = ["Fagus sylvatica", "Salix cinerea", "Quercus robur"]
    assert suggest_names("Fagus silvatica", reference) == ["Fagus sylvatica"]
    assert suggest_names("Salix sinerea", reference) == ["Salix cinerea"]
    assert suggest_names("Tilia cordata", reference) == []
