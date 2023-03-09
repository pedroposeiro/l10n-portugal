Generate Portuguese tax authority legal Invoices ("Faturas") using BILL.

**UPDATE November/2021:**

Invoices:

- Added support to the different documents types:
  Invoice, Invoice Receipt, Simplified Invoice.
  The default document type is set on the Journal,
  and can be changed on the Invoice form.

- Use the invoice commercial partner for the name and address,
  instead of the invoice contact.

- Added support for the Terms and Conditions/Observations field

- Added to Credit Notes the link to the source Invoice


BILL is a paid service.
Visit https://invoicexpress.com for more details.

Once the BILL connection is configured,
the invoice CONFIRM button automatically generates the BILL invoice.

If the BILL Invoice email template is configured,
the BILL service will also send the invoice by email,
using the details in Odoo configured email template.

This replaces the Odoo SEND & PRINT button,
since only the BILL generated document should be used.
Having other print layouts for the invoice is not allowed
by the Portuguese Tax Authority.

Legal transport documents ("Guias de Transporte" e "Guias de Remessa) are also supported
through the extension module "l10n_pt_stock_invoicexpress".
