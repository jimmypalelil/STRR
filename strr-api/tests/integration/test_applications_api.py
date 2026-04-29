"""Integration tests for ``/applications`` endpoints."""

from http import HTTPStatus
from unittest.mock import patch

import pytest

from tests.integration.helpers import (
    load_mock_json,
    resolve_path_for_unauth,
    routes_with_prefix,
    unauthenticated_request,
)
from tests.integration.route_registry import EXPECTED_STRR_API_ROUTES, PUBLIC_ROUTES

_ROWS = routes_with_prefix(EXPECTED_STRR_API_ROUTES - PUBLIC_ROUTES, "/applications")
_ROW_IDS = [f"{m}_{r}".replace("/", "_").replace("<", "").replace(">", "") for m, r in _ROWS]


@pytest.mark.parametrize("method,rule", _ROWS, ids=_ROW_IDS)
def test_applications_routes_require_auth_without_bearer(client, method, rule):
    path = resolve_path_for_unauth(rule)
    rv = unauthenticated_request(client, method, path)
    assert rv.status_code == HTTPStatus.UNAUTHORIZED


@patch("strr_api.services.strr_pay.create_invoice")
@pytest.mark.slow
def test_post_application_with_invoice_mock_returns_success(
    mock_invoice, client, jwt, integration_account_id, mock_invoice_response
):
    mock_invoice.return_value = mock_invoice_response
    from tests.unit.utils.auth_helpers import PUBLIC_USER, create_header

    headers = create_header(jwt, [PUBLIC_USER], "Account-Id")
    headers["Account-Id"] = str(integration_account_id)
    payload = load_mock_json("host_registration.json")
    rv = client.post("/applications", json=payload, headers=headers)
    assert rv.status_code in (HTTPStatus.OK, HTTPStatus.CREATED), rv.get_data(as_text=True)


def test_get_applications_list_ok(client, jwt, integration_account_id):
    from tests.unit.utils.auth_helpers import PUBLIC_USER, create_header

    headers = create_header(jwt, [PUBLIC_USER], "Account-Id")
    headers["Account-Id"] = str(integration_account_id)
    rv = client.get("/applications", headers=headers)
    assert rv.status_code == HTTPStatus.OK
    assert rv.is_json
