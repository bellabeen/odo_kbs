"""Settings → Storage panel. Shell only; logic Phase 6."""

from __future__ import annotations

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    kbs_default_storage_backend_id = fields.Many2one(
        "kbs.storage.backend",
        string="Default Storage Backend",
        config_parameter="kbs_storage.default_backend_id",
    )
