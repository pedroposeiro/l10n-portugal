# Copyright (C) 2021 Open Source Integrators
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class Company(models.Model):
    _inherit = "res.company"

    @api.depends("country_code", "bill_account_name", "bill_api_token")
    def _compute_has_bill(self):
        for company in self:
            company.has_bill = (
                company.country_code == "PT"
                and company.bill_account_name
                and company.bill_api_token
            )

    bill_account_name = fields.Char(string="BILL Account Name")
    bill_api_token = fields.Char(string="BILL API Key")
    has_bill = fields.Boolean(
        compute="_compute_has_bill",
        help="Easy to use indicator if BILL is enabled and can be used",
    )

    bill_template_id = fields.Many2one(
        "mail.template",
        "BILL Email Template",
        domain="[('model', '=', 'account.move')]",
        default=lambda self: self.env.ref(
            "l10n_pt_account_bill.email_template_invoice", False
        ),
        help="Used to generate the To, Cc, Subject and Body"
        " for the email sent by the BILL service",
    )
