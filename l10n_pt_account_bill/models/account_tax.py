# Copyright (C) 2021 Open Source Integrators
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountTax(models.Model):
    _inherit = "account.tax"

    bill_id = fields.Char("BILL ID", copy=False, readonly=True)

    @api.model
    def _map_bill_taxes(self, company):
        """
        Retrieves all BILL taxes, an maps them
        to the existing Odoo taxes
        """
        BILL = self.env["account.bill"]
        response = BILL.call(company, "taxes.json", "GET")
        invx_taxes_dict = {x["name"]: x for x in response.json().get("taxes", [])}
        odoo_taxes = self.search(
            [("type_tax_use", "=", "sale"), ("company_id", "=", company.id)]
        )
        for odoo_tax in odoo_taxes:
            invx_tax_vals = invx_taxes_dict.get(odoo_tax.name)
            if invx_tax_vals:
                odoo_tax._update_bill_status(invx_tax_vals)

    def _prepare_bill_vals(self):
        self.ensure_one()
        tax_data = {
            "tax": {
                "name": self.name,
                "value": str(self.amount),
                "region": self.l10n_pt_fiscal_zone or "",
            }
        }
        return tax_data

    def _update_bill_status(self, result):
        self.bill_id = result.get("id")

    def action_bill_tax_create(self):
        BILL = self.env["account.bill"]
        verb = "POST"
        endpoint = "taxes.json"
        for tax in self.filtered(lambda x: not x.bill_id):
            payload = tax._prepare_bill_vals()
            response = BILL.call(
                tax.company_id, endpoint, verb, payload=payload, raise_errors=False
            )
            if response.status_code == 422:
                # Tax name already exists, map missing bill_ids
                self._map_bill_taxes(tax.company_id)
            else:
                BILL._check_http_status(response)
                response_json = response.json()
                if "tax" in response_json:
                    tax._update_bill_status(response_json["tax"])
