import io

import pytest

from leaf_mlops.storage import LocalStorage, S3Storage, StorageError, get_storage


class FakeS3:
    """Just enough of the boto3 client for S3Storage."""

    def __init__(self):
        self.objects = {}

    def put_object(self, Bucket, Key, Body):
        self.objects[Key] = Body

    def get_object(self, Bucket, Key):
        return {"Body": io.BytesIO(self.objects[Key])}

    def head_object(self, Bucket, Key):
        if Key not in self.objects:
            raise KeyError(Key)

    def delete_object(self, Bucket, Key):
        self.objects.pop(Key, None)

    def get_paginator(self, name):
        objects = self.objects

        class Paginator:
            def paginate(self, Bucket, Prefix):
                yield {"Contents": [{"Key": k} for k in objects if k.startswith(Prefix)]}

        return Paginator()


@pytest.fixture(params=["local", "s3"])
def store(request, tmp_path):
    if request.param == "local":
        return LocalStorage(tmp_path / "media")
    return S3Storage("bucket", client=FakeS3(), prefix="leaves")


def test_save_open_exists_delete(store):
    assert store.save("flavia/1001.jpg", b"abc") == "flavia/1001.jpg"
    assert store.exists("flavia/1001.jpg")
    with store.open("flavia/1001.jpg") as handle:
        assert handle.read() == b"abc"
    store.delete("flavia/1001.jpg")
    assert not store.exists("flavia/1001.jpg")
    store.delete("flavia/1001.jpg")  # deleting twice is fine


def test_save_accepts_file_objects_and_overwrites(store):
    store.save("a/x.bin", io.BytesIO(b"one"))
    store.save("a/x.bin", b"two")
    assert store.open("a/x.bin").read() == b"two"


def test_open_missing_raises(store):
    with pytest.raises(StorageError):
        store.open("nope/missing.jpg")


def test_list_keys_by_prefix(store):
    for key in ("flavia/2.jpg", "flavia/1.jpg", "swedish/1.tif"):
        store.save(key, b"x")
    assert store.list_keys("flavia/") == ["flavia/1.jpg", "flavia/2.jpg"]
    assert len(store.list_keys()) == 3


@pytest.mark.parametrize("key", ["", "/abs.jpg", "../out.jpg", "a/../../out.jpg", "a//b.jpg", "a\\b.jpg"])
def test_unsafe_keys_are_rejected(store, key):
    with pytest.raises(StorageError):
        store.save(key, b"x")


def test_factory_defaults_to_local(tmp_path):
    storage = get_storage({"MEDIA_ROOT": str(tmp_path / "m")})
    assert isinstance(storage, LocalStorage)


def test_factory_rejects_bad_configuration():
    with pytest.raises(StorageError):
        get_storage({"STORAGE_BACKEND": "ftp"})
    with pytest.raises(StorageError):
        get_storage({"STORAGE_BACKEND": "s3"})
