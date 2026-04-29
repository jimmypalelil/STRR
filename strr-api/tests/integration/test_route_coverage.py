"""Guard: STRR API surface matches the maintained route registry."""

from tests.integration.helpers import collect_strr_routes
from tests.integration.route_registry import EXPECTED_STRR_API_ROUTES


def test_url_map_matches_expected_strr_api_routes(app):
    actual = collect_strr_routes(app)
    assert actual == EXPECTED_STRR_API_ROUTES, (
        "Update tests/integration/route_registry.py when routes change.\n"
        f"only in actual: {sorted(actual - EXPECTED_STRR_API_ROUTES)}\n"
        f"only in expected: {sorted(EXPECTED_STRR_API_ROUTES - actual)}"
    )
