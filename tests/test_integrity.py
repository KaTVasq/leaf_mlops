from leaf_mlops.data.integrity import sha256_file, verify_hashes

EMPTY_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def make_file(base, dataset, name, content):
    path = base / dataset / "raw" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def row(dataset, name, sha):
    return {"image_id": f"{dataset}:{name}", "source_dataset": dataset, "file_path": name, "sha256": sha}


def test_sha256_of_empty_file(tmp_path):
    assert sha256_file(make_file(tmp_path, "a", "x.jpg", b"")) == EMPTY_SHA


def test_verify_classifies_every_row(tmp_path):
    good = make_file(tmp_path, "a", "good.jpg", b"one")
    make_file(tmp_path, "a", "edited.jpg", b"original")
    rows = [
        row("a", "good.jpg", sha256_file(good)),
        row("a", "edited.jpg", "0" * 64),
        row("a", "gone.jpg", "1" * 64),
        row("a", "nohash.jpg", ""),
    ]
    result = verify_hashes(rows, tmp_path)
    assert result == {
        "ok": ["a:good.jpg"], "changed": ["a:edited.jpg"],
        "missing": ["a:gone.jpg"], "no_hash": ["a:nohash.jpg"],
    }


def test_modifying_a_file_after_hashing_is_detected(tmp_path):
    path = make_file(tmp_path, "a", "x.jpg", b"before")
    rows = [row("a", "x.jpg", sha256_file(path))]
    assert verify_hashes(rows, tmp_path)["ok"] == ["a:x.jpg"]
    path.write_bytes(b"after")
    assert verify_hashes(rows, tmp_path)["changed"] == ["a:x.jpg"]
