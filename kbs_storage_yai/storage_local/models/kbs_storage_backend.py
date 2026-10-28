"""Extend backend_code selection + register factory (ADR-002)."""

from __future__ import annotations

from odoo import fields, models

from storage_core.registry import get_default_registry

from ..local_driver import LocalStorageDriver


def _local_factory(config: dict) -> LocalStorageDriver:
    return LocalStorageDriver(config)


get_default_registry().register("local", _local_factory)


class KbsStorageBackend(models.Model):
    _inherit = "kbs.storage.backend"

    backend_code = fields.Selection(
        selection_add=[("local", "Local Filesystem")],
        ondelete={"local": "set null"},
    )
    # Reuse `bucket` (root path) and `endpoint` (URL prefix) — no new fields.
