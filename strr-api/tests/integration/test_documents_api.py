"""Integration tests for ``/documents`` endpoints."""

from http import HTTPStatus

import pytest

from tests.integration.helpers import (
    resolve_path_for_unauth,
    routes_with_prefix,
    unauthenticated_request,
)
from tests.integration.route_registry import EXPECTED_STRR_API_ROUTES, PUBLIC_ROUTES

_ROWS = routes_with_prefix(EXPECTED_STRR_API_ROUTES - PUBLIC_ROUTES, "/documents")
_ROW_IDS = [f"{m}_{r}".replace("/", "_") for m, r in _ROWS]


@pytest.mark.parametrize("method,rule", _ROWS, ids=_ROW_IDS)
def test_documents_routes_require_auth_without_bearer(client, method, rule):
    path = resolve_path_for_unauth(rule)
    rv = unauthenticated_request(client, method, path)
    assert rv.status_code == HTTPStatus.UNAUTHORIZED
