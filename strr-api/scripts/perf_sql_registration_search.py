#!/usr/bin/env python3
"""Emit SQL for ``GET /registrations/search`` to stdout (for ``EXPLAIN ANALYZE`` in psql).

Runs a single in-process request with SQLAlchemy ``echo`` on the engine, plus
Python logging on ``sqlalchemy.engine``. Use the printed statements as the
body of::

    EXPLAIN (ANALYZE, BUFFERS) <paste>;

Example::

    cd strr-api
    export DEPLOYMENT_ENV=development
    poetry run python scripts/perf_sql_registration_search.py --case requirement_pr 2>sql.log
    grep -E '^SELECT|^FROM' sql.log | head
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--case",
        default="default_statuses_only",
        help="Name from benchmark_registration_search._matrix()",
    )
    parser.add_argument("--i-know-this-is-local", action="store_true")
    args = parser.parse_args()

    if not args.i_know_this_is_local:
        dep = (os.getenv("DEPLOYMENT_ENV") or "").strip().lower()
        if dep not in {"development", "dev", "local", "sandbox"}:
            raise SystemExit("Set DEPLOYMENT_ENV=development or pass --i-know-this-is-local.")

    from benchmark_registration_search import _matrix  # noqa: E402

    rows = {r["name"]: r["query_string"] for r in _matrix()}
    if args.case not in rows:
        raise SystemExit(f"Unknown case {args.case!r}. Choose one of: {', '.join(sorted(rows))}")

    logging.basicConfig(level=logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)

    from unittest.mock import patch

    from strr_api import create_app
    from strr_api import jwt as jwt_manager
    from strr_api.config import Development, Testing
    from tests.unit.utils.auth_helpers import STRR_EXAMINER, create_header

    class BenchmarkLocalConfig(Development):
        JWT_OIDC_TEST_MODE = True
        JWT_OIDC_TEST_AUDIENCE = Testing.JWT_OIDC_TEST_AUDIENCE
        JWT_OIDC_TEST_ISSUER = Testing.JWT_OIDC_TEST_ISSUER
        JWT_OIDC_TEST_KEYS = Testing.JWT_OIDC_TEST_KEYS
        JWT_OIDC_TEST_PRIVATE_KEY_JWKS = Testing.JWT_OIDC_TEST_PRIVATE_KEY_JWKS
        JWT_OIDC_TEST_PRIVATE_KEY_PEM = Testing.JWT_OIDC_TEST_PRIVATE_KEY_PEM

    app = create_app(BenchmarkLocalConfig)
    with app.app_context():
        from strr_api.models.db import db

        db.engine.echo = True
        client = app.test_client()
        staff_headers = create_header(jwt_manager, [STRR_EXAMINER], "Account-Id")
        with patch(
            "strr_api.resources.registrations.UserService.get_or_create_user_by_jwt",
            return_value=None,
        ):
            client.get("/registrations/search", query_string=list(rows[args.case]), headers=staff_headers)


if __name__ == "__main__":
    main()
