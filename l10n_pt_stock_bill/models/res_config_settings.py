# Copyright (C) 2021 Open Source Integrators
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    bill_delivery_template_id = fields.Many2one(
        related="company_id.bill_delivery_template_id", readonly=False
    )
