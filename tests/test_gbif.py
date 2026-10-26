import json

from leaf_mlops.data.gbif import CachedMatcher, apply_verdicts, verify_entry, verify_mapping
from leaf_mlops.data.mapping import LabelEntry


def entry(species="Ulmus glabra", genus="Ulmus", family="Ulmaceae", key="1"):
    return LabelEntry(key=key, original=species or genus, family=family, genus=genus,
                      species=species, status="proposed_unverified")


def response(name, family="Ulmaceae", genus="Ulmus", status="ACCEPTED", match="EXACT",
             confidence=99, rank="SPECIES", species=None):
    return {"canonicalName": name, "matchType": match, "confidence": confidence, "status": status,
            "rank": rank, "family": family, "genus": genus, "species": species or name}


def matcher(answers, calls=None):
    def fetch(name, rank):
        if calls is not None:
            calls.append((name, rank))
        return answers.get(name, {"matchType": "NONE", "confidence": 0})
    return CachedMatcher(fetch=fetch)


def test_exact_accepted_match_is_verified():
    verdict = verify_entry(entry(), matcher({"Ulmus glabra": response("Ulmus glabra")}))
    assert verdict.status == "verified" and verdict.findings == ()


def test_synonym_needs_review_and_reports_accepted_name():
    answers = {"Ulmus carpinifolia": response("Ulmus carpinifolia", status="SYNONYM", species="Ulmus minor")}
    verdict = verify_entry(entry("Ulmus carpinifolia"), matcher(answers))
    assert verdict.status == "needs_review"
    assert "Ulmus minor" in verdict.message


def test_family_disagreement_needs_review():
    answers = {"Acer rubrum": response("Acer rubrum", family="Sapindaceae", genus="Acer")}
    verdict = verify_entry(entry("Acer rubrum", "Acer", "Aceraceae"), matcher(answers))
    assert verdict.status == "needs_review"
    assert "Sapindaceae" in verdict.message


def test_fuzzy_or_missing_match_needs_review():
    fuzzy = {"Ulmus glabr": response("Ulmus glabra", match="FUZZY", confidence=95)}
    assert verify_entry(entry("Ulmus glabr"), matcher(fuzzy)).status == "needs_review"
    assert verify_entry(entry("Nada nada"), matcher({})).status == "needs_review"


def test_genus_only_entry_is_queried_by_genus_rank():
    calls = []
    answers = {"Quercus": response("Quercus", family="Fagaceae", genus="Quercus", rank="GENUS")}
    verdict = verify_entry(entry(None, "Quercus", "Fagaceae"), matcher(answers, calls))
    assert verdict.status == "verified"
    assert calls == [("Quercus", "GENUS")]


def test_author_in_original_name_is_not_sent_to_gbif():
    calls = []
    answers = {"Berberis anhweiensis": response("Berberis anhweiensis", family="Berberidaceae", genus="Berberis")}
    e = entry("Berberis anhweiensis", "Berberis", "Berberidaceae")
    verify_entry(e, matcher(answers, calls))
    assert calls == [("Berberis anhweiensis", "SPECIES")]


def test_answers_are_cached(tmp_path):
    calls = []
    cache = tmp_path / "cache.json"
    first = CachedMatcher(fetch=lambda n, r: calls.append(n) or response(n), cache_path=cache)
    first.match("Ulmus glabra", "SPECIES")
    first.match("Ulmus glabra", "SPECIES")
    first.save()
    second = CachedMatcher(fetch=lambda n, r: calls.append(n) or response(n), cache_path=cache)
    second.match("Ulmus glabra", "SPECIES")
    assert calls == ["Ulmus glabra"]


def test_apply_verdicts_updates_status_and_keeps_taxonomy(tmp_path):
    path = tmp_path / "mapping.json"
    path.write_text(json.dumps({"taxonomy_source": "Draft.", "classes": {
        "1": {"original": "Ulmus carpinifolia", "family": "Ulmaceae", "genus": "Ulmus",
              "species": "Ulmus carpinifolia", "status": "proposed_unverified", "note": "Hand note."},
        "2": {"original": "Ulmus glabra", "family": "Ulmaceae", "genus": "Ulmus",
              "species": "Ulmus glabra", "status": "proposed_unverified", "note": ""},
    }}), encoding="utf-8")
    answers = {"Ulmus carpinifolia": response("Ulmus carpinifolia", status="SYNONYM", species="Ulmus minor"),
               "Ulmus glabra": response("Ulmus glabra")}
    from leaf_mlops.data.mapping import load_label_mapping
    verdicts = verify_mapping(load_label_mapping(path), matcher(answers))

    assert apply_verdicts(path, verdicts) == 2
    assert apply_verdicts(path, verdicts) == 0  # idempotent

    classes = json.loads(path.read_text(encoding="utf-8"))["classes"]
    assert classes["1"]["status"] == "needs_review" and classes["1"]["note"].startswith("Hand note.")
    assert classes["1"]["species"] == "Ulmus carpinifolia"
    assert classes["2"]["status"] == "verified"


def test_hybrid_sign_is_compared_by_canonical_name():
    answers = {"Populus canadensis": response("Populus canadensis", family="Salicaceae", genus="Populus")}
    e = entry("Populus × canadensis", "Populus", "Salicaceae")
    assert verify_entry(e, matcher(answers)).status == "verified"
