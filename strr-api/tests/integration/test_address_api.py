"""Integration tests for ``/address`` and ``/v1/address`` endpoints."""

from http import HTTPStatus
from unittest.mock import patch

import pytest

from tests.integration.helpers import (
    resolve_path_for_unauth,
    unauthenticated_request,
)
from tests.integration.route_registry import EXPECTED_STRR_API_ROUTES, PUBLIC_ROUTES

_ADDRESS_ROWS = sorted(
    (m, r) for m, r in (EXPECTED_STRR_API_ROUTES - PUBLIC_ROUTES) if r.startswith("/address/")
)
_ADDRESS_IDS = [f"{m}_{r}".replace("/", "_") for m, r in _ADDRESS_ROWS]

_V1_ADDRESS_ROWS = sorted(
    (m, r) for m, r in (EXPECTED_STRR_API_ROUTES - PUBLIC_ROUTES) if r.startswith("/v1/address/")
)
_V1_ADDRESS_IDS = [f"{m}_{r}".replace("/", "_") for m, r in _V1_ADDRESS_ROWS]


@pytest.mark.parametrize("method,rule", _ADDRESS_ROWS, ids=_ADDRESS_IDS)
def test_address_routes_require_auth_without_bearer(client, method, rule):
    path = resolve_path_for_unauth(rule)
    rv = unauthenticated_request(client, method, path)
    assert rv.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.parametrize("method,rule", _V1_ADDRESS_ROWS, ids=_V1_ADDRESS_IDS)
def test_v1_address_routes_require_auth_without_bearer(client, method, rule):
    path = resolve_path_for_unauth(rule)
    rv = unauthenticated_request(client, method, path)
    assert rv.status_code == HTTPStatus.UNAUTHORIZED


@patch("strr_api.resources.str_address_requirements.ApprovalService.getSTRDataForAddress", return_value={"ok": True})
def test_post_address_requirements_ok(mock_str, client, jwt):
    from tests.unit.utils.auth_helpers import PUBLIC_USER, create_header

    headers = create_header(jwt, [PUBLIC_USER])
    body = {
        "address": {
            "unitNumber": "1",
            "streetNumber": "123",
            "streetName": "Main St",
            "city": "Victoria",
            "province": "BC",
            "postalCode": "V8V1A1",
        }
    }
    rv = client.post("/address/requirements", json=body, headers=headers)
    assert rv.status_code == HTTPStatus.OK
