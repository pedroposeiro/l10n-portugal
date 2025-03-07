from unittest.mock import Mock, patch

import requests

from odoo import fields
from odoo.tests import Form, common


def mock_response(json, status_code=200):
    mock_response = Mock()
    mock_response.json.return_value = json
    mock_response.text = str(json)
    mock_response.status_code = status_code
    return mock_response


@common.tagged("-at_install", "post_install")
class TestBILL(common.TransactionCase):
    def setUp(self):
        super().setUp()

        self.company = self.env.company
        self.company.write(
            {
                "bill_account_name": "ACCOUNT",
                "bill_api_token": "APIKEY",
                "country_id": self.env.ref("base.pt").id,
            }
        )
        Journal = self.env["account.journal"]
        self.sale_journals = Journal.search([("type", "=", "sale")])

        self.AccountMove = self.env["account.move"]
        self.ProductProduct = self.env["product.product"]
        self.ResPartner = self.env["res.partner"]
        self.AccountTax = self.env["account.tax"]

        self.productA = self.ProductProduct.create(
            {"name": "Product A", "list_price": "2.0"}
        )
        self.productB = self.ProductProduct.create(
            {"name": "Product B", "list_price": "3.0"}
        )

        self.pt_country = self.env.ref("base.pt")
        self.partnerA = self.ResPartner.create(
            {
                "name": "Customer A",
                "country_id": self.pt_country.id,
                "city": "Porto",
                "zip": "2000-555",
            }
        )

    def test_res_partner__prepare_bill_vals(self):
        partner_PT = self.partnerA.copy({"country_id": self.env.ref("base.pt").id})
        partner_PT_vals = partner_PT._prepare_bill_vals()
        self.assertEqual(
            partner_PT_vals["language"], "pt", "Address in Portugal uses pt language"
        )
        partner_ES = self.partnerA.copy({"country_id": self.env.ref("base.es").id})
        partner_ES_vals = partner_ES._prepare_bill_vals()
        self.assertEqual(
            partner_ES_vals["language"], "es", "Address in Spain uses es language"
        )
        partner_FR = self.partnerA.copy({"country_id": self.env.ref("base.fr").id})
        partner_FR_vals = partner_FR._prepare_bill_vals()
        self.assertEqual(
            partner_FR_vals["language"],
            "en",
            "Address not in Spain or Portugal uses en language",
        )

    def test_010_get_config_and_base_url(self):
        API = self.env["account.bill"]
        url = API._build_url(API._get_config(self.company), "dummy.json")
        self.assertEqual(url, "https://ACCOUNT.app.bill.com/dummy.json")

    @patch.object(requests, "request")
    def test_100_create_bill_tax(self, mock_request):
        mock_request.return_value = mock_response(
            {
                "tax": {
                    "id": 12345,
                    "name": "IVA23",
                    "value": 23.0,
                    "region": "PT",
                    "default_tax": 1,
                }
            }
        )
        taxA = self.env["account.tax"].create(
            {
                "name": "IVA23",
                "type_tax_use": "sale",
                "amount_type": "percent",
                "amount": 23.0,
            }
        )
        taxA.action_bill_tax_create()
        self.assertEqual(taxA.bill_id, "12345")

    @patch.object(requests, "request")
    def test_101_create_bill_invoice(self, mock_request):
        mock_request.return_value = mock_response(
            {
                "invoice_receipt": {
                    "id": 12345678,
                    "inverted_sequence_number": "MYSEQ/123",
                }
            }
        )
        # Ensure Journal is configured
        self.sale_journals.write({"bill_doc_type": "invoice_receipt"})
        # Create the Invoice
        move_form = Form(self.AccountMove.with_context(default_move_type="out_invoice"))
        move_form.invoice_date = fields.Date.today()
        move_form.partner_id = self.partnerA
        products = [self.productA, self.productB]

        for product in products:
            with move_form.invoice_line_ids.new() as line_form:
                line_form.product_id = product
        invoice = move_form.save()
        invoice.action_post()
        self.assertEqual(invoice.bill_doc_type, "invoice_receipt")
        self.assertEqual(invoice.bill_id, "12345678")
        self.assertEqual(invoice.name, "FR MYSEQ/123")
