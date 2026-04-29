"""Integration tests for ``/permits`` and ``/v1/permits`` validation endpoints."""

from http import HTTPStatus
from unittest.mock import patch

import pytest

from tests.integration.helpers import (
    resolve_path_for_unauth,
    unauthenticated_request,
)
from tests.integration.route_registry import EXPECTED_STRR_API_ROUTES, PUBLIC_ROUTES

_LEGACY_ROWS = sorted(
    (m, r) for m, r in (EXPECTED_STRR_API_ROUTES - PUBLIC_ROUTES) if r.startswith("/permits/")
)
_LEGACY_IDS = [f"{m}_{r}".replace("/", "_") for m, r in _LEGACY_ROWS]

_V1_ROWS = sorted(
    (m, r) for m, r in (EXPECTED_STRR_API_ROUTES - PUBLIC_ROUTES) if r.startswith("/v1/permits/")
)
_V1_IDS = [f"{m}_{r}".replace("/", "_") for m, r in _V1_ROWS]


@pytest.mark.parametrize("method,rule", _LEGACY_ROWS, ids=_LEGACY_IDS)
def test_permits_routes_require_auth_without_bearer(client, method, rule):
    path = resolve_path_for_unauth(rule)
    rv = unauthenticated_request(client, method, path)
    assert rv.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.parametrize("method,rule", _V1_ROWS, ids=_V1_IDS)
def test_v1_permits_routes_require_auth_without_bearer(client, method, rule):
    path = resolve_path_for_unauth(rule)
    rv = unauthenticated_request(client, method, path)
    assert rv.status_code == HTTPStatus.UNAUTHORIZED


@patch("strr_api.resources.validation.ValidationService.validate_permit", return_value=({}, HTTPStatus.OK))
def test_validate_permit_legacy_ok(mock_val, client, jwt):
    from tests.unit.utils.auth_helpers import PUBLIC_USER, create_header

    headers = create_header(jwt, [PUBLIC_USER])
    rv = client.post("/permits/:validatePermit", json={"registrationNumber": "X"}, headers=headers)
    assert rv.status_code == HTTPStatus.OK


@patch("strr_api.resources.validation.ValidationService.validate_permit", return_value=({}, HTTPStatus.OK))
def test_validate_permit_v1_ok(mock_val, client, jwt):
    from tests.unit.utils.auth_helpers import PUBLIC_USER, create_header

    headers = create_header(jwt, [PUBLIC_USER])
    rv = client.post("/v1/permits/:validatePermit", json={"registrationNumber": "X"}, headers=headers)
    assert rv.status_code == HTTPStatus.OK
