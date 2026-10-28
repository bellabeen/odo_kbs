"""Cross-module integration: registry + utils + local driver.

No pytest needed. Run: python -m unittest storage_core.tests.test_integration -v

ponytail: drivers + registry + utils only — no Odoo env. Service-layer
integration (ir.attachment end-to-end) requires TransactionCase + DB; that's
CI-with-Odoo scope, not pure-python harness.
"""
from __future__ import annotations

import io
import sys
import tempfile
import types
import unittest
from pathlib import Path


# Repo root (kbs_storage_yai/) on path so absolute imports below resolve.
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Minimal odoo stub — controller chain needs odoo.http at import time.
if "odoo" not in sys.modules:
    odoo = types.ModuleType("odoo")
    odoo.http = types.SimpleNamespace(
        Controller=object, route=lambda *a, **kw: lambda f: f
    )
    odoo.models = types.SimpleNamespace(Model=object, AbstractModel=object, TransientModel=object)
    odoo.fields = types.SimpleNamespace(
        **{k: lambda *a, **kw: None for k in (
            "Char Text Integer Boolean Many2one One2many Selection Datetime "
            "Float Binary Html Date Many2many".split())}
    )
    odoo.api = types.SimpleNamespace(model=lambda f: f)
    odoo.exceptions = types.SimpleNamespace(AccessError=Exception, NotFound=Exception)
    sys.modules["odoo"] = odoo
    sys.modules["odoo.http"] = types.ModuleType("odoo.http")
    sys.modules["odoo.http"].Response = lambda *a, **kw: None
    sys.modules["odoo.http"].request = types.SimpleNamespace(env=None, uid=None)
    sys.modules["odoo.exceptions"] = types.ModuleType("odoo.exceptions")
    sys.modules["odoo.exceptions"].AccessError = Exception
    sys.modules["odoo.exceptions"].NotFound = Exception

from storage_core.domain import ObjectMetadata  # noqa: E402

from storage_core.exceptions import (  # noqa: E402
    ObjectNotFoundError,
    StorageConfigurationError,
)
from storage_core.registry import BackendRegistry  # noqa: E402
from storage_core.utils import sha256_bytes, sha256_stream  # noqa: E402
from storage_local.local_driver import LocalStorageDriver  # noqa: E402


class TestLocalIntegration(unittest.TestCase):
    """Registry → driver → utils glued. Uses tempdir per test."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        reg = BackendRegistry()
        reg.register("local", lambda cfg: LocalStorageDriver(cfg))
        self.driver = reg.get("local", {"root": self._tmp.name, "bucket": "t"})

    def test_write_read_roundtrip(self) -> None:
        key, payload = "a/b.bin", b"hello world"
        md = self.driver.write(key, payload)
        self.assertIsInstance(md, ObjectMetadata)
        self.assertEqual(md.object_key, key)
        self.assertEqual(md.checksum, sha256_bytes(payload))
        self.assertEqual(md.size, len(payload))
        self.assertEqual(self.driver.read(key), payload)

    def test_dedup_identical_payloads(self) -> None:
        """ADR-006: same content → same checksum, regardless of key."""
        payload = b"dedup"
        m1 = self.driver.write("one", payload)
        m2 = self.driver.write("two", payload)
        self.assertEqual(m1.checksum, m2.checksum)
        self.assertEqual(m1.checksum, sha256_bytes(payload))
        self.assertEqual(self.driver.read("one"), payload)
        self.assertEqual(self.driver.read("two"), payload)

    def test_stream_matches_bytes(self) -> None:
        payload = b"x" * (512 * 1024)
        md = self.driver.write("big", payload)
        self.assertEqual(md.checksum, sha256_stream(io.BytesIO(payload)))
        chunks = list(self.driver.stream("big", chunk_size=64 * 1024))
        self.assertEqual(b"".join(chunks), payload)

    def test_delete_and_exists(self) -> None:
        self.driver.write("k", b"v")
        self.assertTrue(self.driver.exists("k"))
        self.driver.delete("k")
        self.assertFalse(self.driver.exists("k"))
        with self.assertRaises(ObjectNotFoundError):
            self.driver.read("k")

    def test_list_by_prefix(self) -> None:
        for k in ("p/a", "p/b", "q/c"):
            self.driver.write(k, b"1")
        keys = sorted(self.driver.list("p/"))
        self.assertEqual(keys, ["p/a", "p/b"])

    def test_copy_and_move(self) -> None:
        self.driver.write("src", b"data")
        cp = self.driver.copy("src", "cp")
        self.assertEqual(cp.object_key, "cp")
        self.assertTrue(self.driver.exists("src"))
        mv = self.driver.move("src", "mv")
        self.assertEqual(mv.object_key, "mv")
        self.assertFalse(self.driver.exists("src"))
        self.assertEqual(self.driver.read("mv"), b"data")

    def test_driver_requires_root(self) -> None:
        reg = BackendRegistry()
        reg.register("local2", lambda cfg: LocalStorageDriver(cfg))
        with self.assertRaises(StorageConfigurationError):
            reg.get("local2", {})

    def test_healthcheck(self) -> None:
        self.assertTrue(self.driver.healthcheck())


if __name__ == "__main__":
    unittest.main()
