# Copyright (C) 2021 Open Source Integrators
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import _, api, exceptions, fields, models
from odoo.tools import format_datetime

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    @api.depends("picking_type_id", "company_id.has_bill")
    def _compute_can_bill(self):
        for delivery in self:
            delivery.can_bill = (
                delivery.company_id.has_bill
                and delivery.bill_doc_type
            )

    @api.depends("can_bill", "company_id.bill_delivery_template_id")
    def _compute_can_bill_email(self):
        for delivery in self:
            delivery.can_bill_email = (
                delivery.can_bill
                and delivery.company_id.bill_delivery_template_id
            )

    @api.depends("can_bill_email", "bill_doc_type")
    def _compute_bill_send_email(self):
        for delivery in self:
            delivery.bill_send_email = (
                delivery.can_bill_email
                and delivery.bill_doc_type != "devolution"
            )

    @api.depends("scheduled_date")
    def _compute_l10npt_transport_doc_due_date(self):
        for doc in self:
            doc.l10npt_transport_doc_due_date = fields.Date.add(
                doc.scheduled_date, days=7
            )

    @api.depends("picking_type_id")
    def _compute_bill_doc_type(self):
        """
        Return the doc type, read from the Operation Type.
        Also detect devolutions, and then use the appropriate type instead.
        """
        for pick in self:
            pick_doc_type = pick.picking_type_id.bill_doc_type
            country = pick.partner_id.country_id
            is_PT = not country or country.code == "PT"
            # TODO: Automatic support for devolutions
            # Disabled for now, should be used for supplier devolutions only?
            # return_orig_moves = pick.move_ids_without_package.origin_returned_move_id
            # if return_orig_moves.mapped("picking_id.bill_id"):
            #     pick.bill_doc_type = "devolution"
            if pick_doc_type and pick_doc_type != "none" and is_PT:
                pick.bill_doc_type = pick_doc_type

    license_plate = fields.Char()
    bill_id = fields.Char("Bill ID", copy=False, readonly=True)
    bill_number = fields.Char(
        "Bill Number", copy=False, readonly=True
    )
    bill_permalink = fields.Char(
        "Bill Doc Link", copy=False, readonly=True
    )
    l10npt_transport_doc_due_date = fields.Date(
        "Transport Doc. Validity",
        compute="_compute_l10npt_transport_doc_due_date",
        store=True,
        readonly=False,
    )
    can_bill = fields.Boolean(compute="_compute_can_bill")
    can_bill_email = fields.Boolean(compute="_compute_can_bill_email")
    bill_send_email = fields.Boolean(
        "InvX Send Email",
        compute="_compute_bill_send_email",
        store=True,
        readonly=False,
        copy=False,
        help="If unchecked, both the Bill email"
        " and the Delivery email won't be sent.",
    )
    bill_doc_type = fields.Selection(
        [
            ("transport", "Guia de Transporte / Transport"),
            ("shipping", "Guia de Remessa / Shipping"),
            ("devolution", "Devolução / Return"),
        ],
        string="InvX Doc Type",
        compute="_compute_bill_doc_type",
        store=True,
        readonly=False,
        copy=False,
        help="Select the type of legal delivery document"
        " to be created by Bill.",
    )

    def _send_confirmation_email(self):
        # Only send Delivery emails if the Bill checkbox is selected
        to_send = self.filtered("bill_send_email")
        super(StockPicking, to_send)._send_confirmation_email()

    @api.model
    def _get_bill_prefix(self, doctype):
        return {
            "transport": "GT",
            "shipping": "GR",
            "devolution": "GD",
        }.get(doctype)

    def _prepare_bill_lines(self):
        lines = self.move_lines.filtered("quantity_done")
        # Ensure Taxes are created on Bill
        lines.mapped("sale_line_id.tax_id").action_bill_tax_create()
        items = []
        for line in lines:
            tax = line.sale_line_id.tax_id[:1]
            # tax_detail = {"name": tax.name, "value": tax.amount} if tax else {}
            tax_detail = {"name": tax.name} if tax else {}
            items.append(
                {
                    "name": line.product_id.default_code
                    or line.product_id.display_name,
                    "description": line.product_id.name or "",  # line.name for SO desc
                    # TODO: add an option to allow having the prices set?
                    "unit_price": 0.0,  # line.sale_line_id.price_unit,
                    "quantity": line.quantity_done,
                    "discount": line.sale_line_id.discount,
                    "tax": tax_detail,
                }
            )
        return items

    def _prepare_bill_vals(self):
        self.ensure_one()
        shipping_date = fields.Datetime.add(fields.Datetime.now(), minutes=5)
        if shipping_date < fields.Datetime.now():
            raise exceptions.ValidationError(
                _("Scheduled Date should be bigger then current datetime!")
            )
        customer = self.partner_id.commercial_partner_id
        customer_vals = customer.set_bill_contact()
        if self.location_id.usage == "internal":  # Outgoing
            address_from = self.picking_type_id.warehouse_id.partner_id
            address_to = self.partner_id
        elif self.location_dest_id.usage == "internal":  # Incoming => Return
            address_from = self.partner_id
            address_to = self.picking_type_id.warehouse_id.partner_id
        addr_from_vals = address_from._prepare_bill_shipping_vals()
        addr_to_vals = address_to._prepare_bill_shipping_vals()

        doctype = self.bill_doc_type
        item_vals = self._prepare_bill_lines()
        return {
            doctype: {
                "date": shipping_date.strftime("%d/%m/%Y"),
                "due_date": (
                    self.l10npt_transport_doc_due_date or shipping_date
                ).strftime("%d/%m/%Y"),
                "loaded_at": format_datetime(
                    self.env, shipping_date, dt_format="dd/MM/yyyy HH:mm:ss"
                ),
                "license_plate": self.license_plate or "",
                "address_from": addr_from_vals,
                "address_to": addr_to_vals,
                "reference": self.origin or "",
                "client": customer_vals,
                "items": item_vals,
            }
        }

    def _update_bill_status(self):
        inv_xpress_link_name = _("View Document")
        inv_xpress_link = _(
            "<a class='btn btn-info mr-2' target='new' href={}>{}</a>"
        ).format(self.bill_permalink, inv_xpress_link_name)
        msg = _(
            "Bill record has been created for this delivery order:<ul>"
            "<li>Number: {inv_xpress_num}</li>"
            "<li>{inv_xpress_link}</li></ul>"
        ).format(
            inv_xpress_num=self.bill_number, inv_xpress_link=inv_xpress_link
        )
        self.message_post(body=msg)

    def action_create_bill_delivery(self):
        """
        Generate legal "Guia de Transporte", for customer deliveries
        or transfers between warehouses.
        We allow generating more than one for the same Odoo document.
        """
        Bill = self.env["account.bill"]
        for delivery in self.filtered("can_bill"):
            payload = delivery._prepare_bill_vals()
            doctype = delivery.bill_doc_type
            response = Bill.call(
                delivery.company_id, "{}s.json".format(doctype), "POST", payload=payload
            )
            values = response.json().get(doctype)
            if not values:
                raise exceptions.UserError(
                    _("Something went wrong: the Bill response looks empty.")
                )
            delivery.bill_id = values.get("id")
            delivery.bill_permalink = values.get("permalink")
            response1 = Bill.call(
                delivery.company_id,
                "{}s/{}/change-state.json".format(doctype, values["id"]),
                "PUT",
                payload={doctype: {"state": "finalized"}},
            )
            values1 = response1.json().get(doctype)
            prefix = self._get_bill_prefix(doctype)
            seqnum = values1["inverted_sequence_number"]
            invx_number = "%s %s" % (prefix, seqnum)
            delivery.bill_number = invx_number
            delivery._update_bill_status()

    def _prepare_bill_email_vals(self, ignore_no_config=False):
        self.ensure_one()
        template_id = self.company_id.bill_delivery_template_id
        values = template_id.generate_email(
            self.id, ["subject", "body_html", "email_to", "email_cc"]
        )
        if not template_id and not ignore_no_config:
            raise exceptions.UserError(
                _(
                    "Please configure the Bill Delivery email template"
                    " at Settings > General Setting, Bill section"
                )
            )
        if not values.get("email_to") and not ignore_no_config:
            raise exceptions.UserError(
                _("No address to send delivery document email to.")
            )
        email_data = None
        if template_id and values["email_to"]:
            email_data = {
                "message": {
                    "client": {"email": values["email_to"], "save": "0"},
                    "cc": values["email_cc"],
                    "subject": values["subject"],
                    "body": values["body_html"],
                }
            }
        return email_data

    def action_send_bill_delivery(self, ignore_no_config=False):
        Bill = self.env["account.bill"]
        for delivery in self.filtered("bill_send_email"):
            if not delivery.bill_id:
                raise exceptions.UserError(
                    _("Delivery %s is not registered in Bill yet."),
                    delivery.name,
                )
            doctype = delivery.bill_doc_type
            endpoint = "{}s/{}/email-document.json".format(
                doctype, delivery.bill_id
            )
            payload = delivery._prepare_bill_email_vals(ignore_no_config)
            if payload:
                Bill.call(
                    delivery.company_id, endpoint, "PUT", payload=payload
                )
                msg = _(
                    "Email sent by Bill:<ul><li>To: {}</li><li>Cc: {}</li></ul>"
                ).format(
                    payload["message"]["client"]["email"],
                    payload["message"]["cc"] or _("None"),
                )
                delivery.message_post(body=msg)

    def button_validate(self):
        """
        Automatically generate legal transport docs for PT customers
        """
        res = super().button_validate()
        if res is True:  # do not enter if the result is a dict, only if it is True
            to_bill = self.filtered(
                lambda x: x.partner_id.country_id.code == "PT"
            )
            to_bill.action_create_bill_delivery()
            to_bill.action_send_bill_delivery(ignore_no_config=True)
        return res
