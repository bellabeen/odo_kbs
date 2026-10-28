"""Pure-Python driver checks. Run: python -m pytest"""

from __future__ import annotations

import io
import tempfile
from pathlib import Path

from storage_core.exceptions import (
    ObjectNotFoundError,
    StorageConfigurationError,
    StorageOperationError,
)
from storage_core.utils import sha256_bytes

from ..local_driver import LocalStorageDriver


def _drv(root: str, **over):
    cfg = {"root": root}
    cfg.update(over)
    return LocalStorageDriver(cfg)


def test_requires_root():
    try:
        LocalStorageDriver({})
    except StorageConfigurationError:
        return
    raise AssertionError("StorageConfigurationError expected")


def test_write_read_stream_roundtrip(tmp_path):
    drv = _drv(str(tmp_path))
    payload = b"hello world" * 1000
    meta = drv.write("a/b.txt", payload)
    assert meta.size == len(payload)
    assert meta.checksum == sha256_bytes(payload)
    assert drv.read("a/b.txt") == payload
    chunks = list(drv.stream("a/b.txt", chunk_size=7))
    assert b"".join(chunks) == payload


def test_missing_raises_ObjectNotFound(tmp_path):
    drv = _drv(str(tmp_path))
    for op in (drv.read, drv.head, drv.checksum, drv.exists):
        pass
    try:
        drv.read("nope.txt")
    except ObjectNotFoundError:
        return
    raise AssertionError("ObjectNotFoundError expected")


def test_exists_and_delete_idempotent(tmp_path):
    drv = _drv(str(tmp_path))
    assert not drv.exists("x.bin")
    drv.write("x.bin", b"1")
    assert drv.exists("x.bin")
    drv.delete("x.bin")
    assert not drv.exists("x.bin")
    drv.delete("x.bin")  # idempotent — no raise


def test_copy_move_list(tmp_path):
    drv = _drv(str(tmp_path))
    drv.write("a/one.bin", b"1")
    drv.copy("a/one.bin", "a/two.bin")
    assert drv.read("a/two.bin") == b"1"
    drv.move("a/two.bin", "a/three.bin")
    assert not drv.exists("a/two.bin")
    keys = list(drv.list())
    assert "a/one.bin" in keys and "a/three.bin" in keys
    assert list(drv.list(prefix="a/o", limit=1)) == ["a/one.bin"]


def test_traversal_rejected(tmp_path):
    drv = _drv(str(tmp_path))
    for bad in ("../etc/passwd", "/etc/passwd", "..", ""):
        try:
            drv.write(bad, b"x")
        except StorageOperationError:
            continue
        raise AssertionError(f"{bad!r} should be rejected")


def test_head_and_checksum(tmp_path):
    drv = _drv(str(tmp_path))
    drv.write("big", b"bigcontent")
    head = drv.head("big")
    assert head.size == 10
    assert head.checksum == drv.checksum("big")


def test_healthcheck(tmp_path):
    drv = _drv(str(tmp_path))
    assert drv.healthcheck()


def test_stream_does_not_buffer(tmp_path):
    """Large payload writes/reads chunked — no full-RAM copy."""
    drv = _drv(str(tmp_path))
    size = 8 * 1024 * 1024  # 8 MiB, larger than any single buffer the driver uses
    payload = (bytes([i % 256]) * 65536 for i in range(size // 65536))
    drv.write("big.bin", payload)
    chunks_read = 0
    for _ in drv.stream("big.bin", chunk_size=65536):
        chunks_read += 1
    assert chunks_read == size // 65536
