# Copyright (C) 2021 Open Source Integrators
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    @api.depends("bill_doc_type")
    def _compute_use_bill(self):
        for journal in self:
            journal.use_bill = (
                journal.bill_doc_type
                and journal.bill_doc_type != "none"
                and journal.company_id.has_bill
            )

    bill_doc_type = fields.Selection(
        [
            ("invoice", "Invoice"),
            ("invoice_receipt", "Invoices Receipt"),
            ("simplified_invoice", "Simplified Invoice"),
            ("none", "No BILL document"),
        ],
        help="Select the type of legal invoice document"
        " to be created by BILL.",
    )
    use_bill = fields.Boolean(
        compute="_compute_use_bill",
        help="Bill service is only used if checked."
        " Only relevant for Sales journals.",
    )
