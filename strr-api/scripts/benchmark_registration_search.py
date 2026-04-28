#!/usr/bin/env python3
"""HTTP-style benchmarks for ``GET /registrations/search`` (in-process Flask test client).

Uses the same JWT test utilities as the API unit tests so you do not need a
running Keycloak instance. Requires a populated database (run
``scripts/perf_seed_registrations.py`` first for volume).

Example::

    cd strr-api
    export DEPLOYMENT_ENV=development
    poetry run python scripts/benchmark_registration_search.py --output baseline-http.json

Compare before/after code changes by re-running with the same flags and a
different ``--output`` path, then ``diff`` the JSON files.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# So ``import tests.*`` resolves when cwd is strr-api (poetry project root).
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _default_status_params() -> list[tuple[str, str]]:
    return [
        ("status", "ACTIVE"),
        ("status", "SUSPENDED"),
        ("status", "CANCELLED"),
        ("status", "EXPIRED"),
    ]


def _matrix() -> list[dict]:
    """Query strings aligned with examiner ``buildRegistrationQueryParams`` / sub-status filters."""
    base = [
        ("limit", "50"),
        ("page", "1"),
        ("sortOrder", "asc"),
    ]
    rows: list[dict] = [
        {
            "name": "default_statuses_only",
            "query_string": _default_status_params() + base,
        },
        {
            "name": "substatus_review_queue",
            "query_string": _default_status_params()
            + base
            + [
                ("approvalMethod", "PROVISIONALLY_APPROVED"),
                ("approvalMethod", "PROVISIONAL_REVIEW"),
                ("examinerReviewed", "false"),
            ],
        },
        {
            "name": "substatus_review_renew",
            "query_string": _default_status_params() + base + [("reviewRenew", "true")],
        },
        {
            "name": "requirement_pr",
            "query_string": _default_status_params() + base + [("requirement", "PR")],
        },
        {
            "name": "requirement_pr_and_bl",
            "query_string": _default_status_params()
            + base
            + [
                ("requirement", "PR"),
                ("requirement", "BL"),
            ],
        },
        {
            "name": "localgov_maple",
            "query_string": _default_status_params() + base + [("localGov", "Maple")],
        },
        {
            "name": "text_search",
            "query_string": _default_status_params() + base + [("text", "Perf")],
        },
        {
            "name": "registration_type_host",
            "query_string": _default_status_params()
            + base
            + [
                ("registrationType", "HOST"),
            ],
        },
        {
            "name": "noc_pending",
            "query_string": _default_status_params() + base + [("nocStatus", "NOC_PENDING")],
        },
        {
            "name": "combined_pr_localgov",
            "query_string": _default_status_params()
            + base
            + [
                ("requirement", "PR"),
                ("localGov", "Surrey"),
            ],
        },
    ]
    return rows


def _assert_local(*, force: bool) -> None:
    if force:
        return
    dep = (os.getenv("DEPLOYMENT_ENV") or "").strip().lower()
    if dep not in {"development", "dev", "local", "sandbox"}:
        raise SystemExit("Set DEPLOYMENT_ENV=development (or pass --i-know-this-is-local) before benchmarking.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=3, help="Runs per matrix row (median reported).")
    parser.add_argument("--output", type=Path, default=None, help="Write JSON results here.")
    parser.add_argument("--i-know-this-is-local", action="store_true")
    args = parser.parse_args()
    _assert_local(force=args.i_know_this_is_local)

    from strr_api import create_app
    from strr_api.config import Development, Testing

    class BenchmarkLocalConfig(Development):
        """Use local ``DATABASE_*`` from ``Development`` plus JWT test keys (like ``Testing``)."""

        JWT_OIDC_TEST_MODE = True
        JWT_OIDC_TEST_AUDIENCE = Testing.JWT_OIDC_TEST_AUDIENCE
        JWT_OIDC_TEST_ISSUER = Testing.JWT_OIDC_TEST_ISSUER
        JWT_OIDC_TEST_KEYS = Testing.JWT_OIDC_TEST_KEYS
        JWT_OIDC_TEST_PRIVATE_KEY_JWKS = Testing.JWT_OIDC_TEST_PRIVATE_KEY_JWKS
        JWT_OIDC_TEST_PRIVATE_KEY_PEM = Testing.JWT_OIDC_TEST_PRIVATE_KEY_PEM

    from strr_api import jwt as jwt_manager
    from tests.unit.utils.auth_helpers import STRR_EXAMINER, create_header

    app = create_app(BenchmarkLocalConfig)
    matrix = _matrix()
    git_sha = _git_sha()

    results: list[dict] = []
    perf_prefixed_count: int | None = None
    with app.app_context():
        from strr_api.models import Registration
        from strr_api.models.db import db

        perf_prefixed_count = (
            db.session.query(Registration).filter(Registration.registration_number.like("PERF%")).count()
        )

        client = app.test_client()
        staff_headers = create_header(jwt_manager, [STRR_EXAMINER], "Account-Id")

        def run_one(qs: list[tuple[str, str]]) -> tuple[float, int, int]:
            from unittest.mock import patch

            with patch(
                "strr_api.resources.registrations.UserService.get_or_create_user_by_jwt",
                return_value=None,
            ):
                t0 = time.perf_counter()
                rv = client.get("/registrations/search", query_string=qs, headers=staff_headers)
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return elapsed_ms, rv.status_code, len(rv.data)

        for row in matrix:
            times: list[float] = []
            status_code = 0
            nbytes = 0
            for _ in range(args.iterations):
                ms, sc, nb = run_one(list(row["query_string"]))
                times.append(ms)
                status_code = sc
                nbytes = nb
            median = statistics.median(times)
            results.append(
                {
                    "name": row["name"],
                    "median_ms": round(median, 2),
                    "min_ms": round(min(times), 2),
                    "max_ms": round(max(times), 2),
                    "http_status": status_code,
                    "response_bytes": nbytes,
                }
            )

    payload = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "git_sha": git_sha,
        "deployment_env": os.getenv("DEPLOYMENT_ENV"),
        "strr_registration_search_skip_application_batch": os.environ.get(
            "STRR_REGISTRATION_SEARCH_SKIP_APPLICATION_BATCH"
        ),
        "perf_prefixed_registration_count": perf_prefixed_count,
        "iterations_per_row": args.iterations,
        "results": results,
    }
    text = json.dumps(payload, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
        print(f"wrote {args.output}", flush=True)
    print(text)


def _git_sha() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=_ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


if __name__ == "__main__":
    main()
