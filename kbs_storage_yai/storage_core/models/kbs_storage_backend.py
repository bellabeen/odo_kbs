"""kbs.storage.backend — backend configuration record (Phase 2 locked name).

Fields only. Behavior (test connection, health check, credential decode)
arrives with the service layer in Phase 6.
"""

from __future__ import annotations

from odoo import fields, models


class KbsStorageBackend(models.Model):
    _name = "kbs.storage.backend"
    _description = "Storage Backend Configuration"
    _order = "sequence, id"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    backend_code = fields.Selection(
        selection=[],
        required=True,
        help="Filled by provider modules via selection_extend (ADR-002).",
    )
    is_default = fields.Boolean(default=False)
    company_id = fields.Many2one("res.company", index=True)
    bucket = fields.Char(help="Bucket / container / root path.")
    region = fields.Char()
    endpoint = fields.Char(help="Custom endpoint for S3-compatible stores.")
    options_json = fields.Text(
        default="{}",
        help="Provider-specific settings. Provider modules validate schema.",
    )
    # Phase 6 wires: credentials via ir.config_parameter key, healthcheck,
    # test_connection() button. See prompt.md §Configuration.
