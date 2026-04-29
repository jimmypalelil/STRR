"""Integration tests for ``/accounts`` endpoints."""

from http import HTTPStatus
from unittest.mock import patch

import pytest

from tests.integration.helpers import (
    resolve_path_for_unauth,
    routes_with_prefix,
    unauthenticated_request,
)
from tests.integration.route_registry import EXPECTED_STRR_API_ROUTES, PUBLIC_ROUTES

_ROWS = routes_with_prefix(EXPECTED_STRR_API_ROUTES - PUBLIC_ROUTES, "/accounts")
_ROW_IDS = [f"{m}_{r}".replace("/", "_") for m, r in _ROWS]


@pytest.mark.parametrize("method,rule", _ROWS, ids=_ROW_IDS)
def test_accounts_routes_require_auth_without_bearer(client, method, rule):
    path = resolve_path_for_unauth(rule)
    rv = unauthenticated_request(client, method, path)
    assert rv.status_code == HTTPStatus.UNAUTHORIZED


@patch("strr_api.resources.account.AuthService.get_user_accounts", return_value=[])
def test_get_user_accounts_ok(mock_get, client, jwt, integration_account_id):
    from tests.unit.utils.auth_helpers import PUBLIC_USER, create_header

    headers = create_header(jwt, [PUBLIC_USER], "Account-Id")
    headers["Account-Id"] = str(integration_account_id)
    rv = client.get("/accounts/", headers=headers)
    assert rv.status_code == HTTPStatus.OK


@patch("strr_api.resources.account.AuthService.search_accounts", return_value=[])
def test_search_accounts_ok(mock_search, client, jwt):
    from tests.unit.utils.auth_helpers import STRR_EXAMINER, create_header

    headers = create_header(jwt, [STRR_EXAMINER])
    rv = client.get("/accounts/search?name=testco", headers=headers)
    assert rv.status_code == HTTPStatus.OK
