# Copyright (C) 2021 Open Source Integrators
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
# Reference: https://github.com/bitmario/bill-api-python

import logging
import pprint
import requests
from werkzeug.urls import url_join

from odoo import _, exceptions, models

_logger = logging.getLogger(__name__)


class BILL(models.AbstractModel):
    _name = "account.bill"
    _description = "BILL connector"

    def _get_config(self, company):
        account_name = company.bill_account_name
        api_token = company.bill_api_token
        if not account_name or not api_token:
            error_msg = _(
                """Something went wrong on API key. You should check the field
                %(field:res.config.settings.bill_account_name)s in
                %(menu:base_setup.menu_config)s."""
            )
            raise self.env["res.config.settings"].get_config_warning(error_msg)
        return {"account_name": account_name, "api_token": api_token}

    def _build_url(self, config, path):
        # For PROD would be app.bill.pt
        if path.startswith('documentos/download'):
            base_url = "https://dev.bill.pt/"
        else:
            base_url = "https://dev.bill.pt/api/1.0/"
        
        return url_join(base_url, path)

    def _build_params(self, config, params_add):
        params = {"api_token": config["api_token"]}
        if params_add:
            params.update(params_add)
        return params

    def _check_http_status(self, response):
        """
        You can perform up to 100 requests per minute for each Account. If you exceed
        this limit, you’ll get a 429 Too Many Requests response for subsequent requests.

        We recommend you handle 429 responses so your integration retries requests
        automatically.
        """
        # TODO: implement request rate limit
        if response.status_code not in [200, 201]:
            raise exceptions.ValidationError(
                _(
                    "Error running API request ({} {}):\n{}".format(
                        response.status_code, response.reason, response.json()
                    )
                )
            )

    def call(self, company, endpoint, verb="GET", payload=None, raise_errors=True):
        config = self._get_config(company)
        request_url = self._build_url(config, endpoint)
        request_params = self._build_params(config, payload)

        _logger.debug(
            "\nRequest for %s %s:\n%s",
            request_url,
            verb,
            pprint.pformat(payload, indent=1),
        )

        response = requests.request(
                verb,
                request_url,
                params=request_params
            )

        _logger.debug(
            "\nResponse %s: %s",
            response.status_code,
            pprint.pformat(response.json(), indent=1)
            if response.text.startswith("{")
            else response.text,
        )
        if raise_errors:
            self._check_http_status(response)
        return response
