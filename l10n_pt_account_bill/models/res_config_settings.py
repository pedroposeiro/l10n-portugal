# Copyright (C) 2021 Open Source Integrators

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    bill_account_name = fields.Char(
        related="company_id.bill_account_name",
        readonly=False,
    )
    bill_api_token = fields.Char(
        related="company_id.bill_api_token",
        readonly=False,
    )
    bill_template_id = fields.Many2one(
        related="company_id.bill_template_id", readonly=False
    )
