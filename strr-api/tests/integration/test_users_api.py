"""Integration tests for ``/users`` endpoints."""

from http import HTTPStatus
from unittest.mock import patch

import pytest

from tests.integration.helpers import (
    resolve_path_for_unauth,
    routes_with_prefix,
    unauthenticated_request,
)
from tests.integration.route_registry import EXPECTED_STRR_API_ROUTES, PUBLIC_ROUTES

_ROWS = routes_with_prefix(EXPECTED_STRR_API_ROUTES - PUBLIC_ROUTES, "/users")
_ROW_IDS = [f"{m}_{r}".replace("/", "_") for m, r in _ROWS]


@pytest.mark.parametrize("method,rule", _ROWS, ids=_ROW_IDS)
def test_users_routes_require_auth_without_bearer(client, method, rule):
    path = resolve_path_for_unauth(rule)
    rv = unauthenticated_request(client, method, path)
    assert rv.status_code == HTTPStatus.UNAUTHORIZED


@patch("strr_api.resources.users.AuthService.get_user_tos", return_value={"isTermsOfUseAccepted": True})
def test_get_user_tos_ok(mock_tos, client, jwt):
    from tests.unit.utils.auth_helpers import PUBLIC_USER, create_header

    headers = create_header(jwt, [PUBLIC_USER])
    rv = client.get("/users/tos", headers=headers)
    assert rv.status_code == HTTPStatus.OK
