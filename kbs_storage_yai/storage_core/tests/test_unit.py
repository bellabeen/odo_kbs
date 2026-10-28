"""Pure-Python unit checks — no Odoo DB. Run: python -m pytest"""

from __future__ import annotations

import io

from storage_core.exceptions import BackendNotFoundError
from storage_core.registry import BackendRegistry
from storage_core.utils import sha256_bytes, sha256_stream
from storage_core.interfaces import StorageBackend
from storage_core.domain import ObjectMetadata


def test_sha256_bytes() -> None:
    assert sha256_bytes(b"") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert sha256_bytes(b"abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_sha256_stream_matches_bytes() -> None:
    payload = b"x" * (256 * 1024)
    assert sha256_stream(io.BytesIO(payload)) == sha256_bytes(payload)
    assert sha256_stream(iter([payload])) == sha256_bytes(payload)


def test_registry_roundtrip() -> None:
    class _Fake(StorageBackend):
        backend_code = "fake"

        def write(self, key, payload, *, mime=None, metadata=None):
            return ObjectMetadata(backend="fake", bucket="b", object_key=key, checksum="c", size=0)

        def read(self, key): return b""
        def stream(self, key, chunk_size=8192): return iter([b""])
        def delete(self, key): pass
        def exists(self, key): return False
        def head(self, key): return ObjectMetadata(backend="fake", bucket="b", object_key=key, checksum="c", size=0)
        def copy(self, s, t): return ObjectMetadata(backend="fake", bucket="b", object_key=t, checksum="c", size=0)
        def move(self, s, t): return ObjectMetadata(backend="fake", bucket="b", object_key=t, checksum="c", size=0)
        def list(self, prefix="", limit=None): return iter([])
        def checksum(self, key): return "c"
        def healthcheck(self): return True

    reg = BackendRegistry()
    reg.register("fake", lambda cfg: _Fake())
    assert reg.has("fake")
    assert "fake" in reg.codes()
    obj = reg.get("fake")
    assert isinstance(obj, StorageBackend)
    assert obj.backend_code == "fake"


def test_registry_missing() -> None:
    reg = BackendRegistry()
    try:
        reg.get("nope")
    except BackendNotFoundError:
        return
    raise AssertionError("BackendNotFoundError expected")
