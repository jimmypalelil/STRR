[![License](https://img.shields.io/badge/License-BSD%203%20Clause-blue.svg)](../LICENSE)
[![Lifecycle:Experimental](https://img.shields.io/badge/Lifecycle-Experimental-339999)](<Redirect-URL>)


# Application Name
Short-Term Rental Registry (STRR)

# INTIAL SETUP
- global install python 3.11
- global install poetry using `pip3.11 install poetry`
- create `strr` postgres db
- run:
```
python -m venv .venv
source .venv/bin/activate
poetry config virtualenvs.in-project true
poetry install
pip3.11 install psycopg2-binary
```
- use `make` to build docker images

## Technology Stack Used
* Python, Flask
* Postgres -  SQLAlchemy, psycopg2-binary & alembic

# setup
Fork the repo and submitted a PR with accompanning tests.
```bash
gh repo fork bcgov/business-transparency-registry
```

Set to use the local repo for the virtual environment
```bash
poetry config virtualenvs.in-project true
```
Install the dependencies
```bash
poetry install
```

Configure the .env

### manage the DB
```bash
poetry shell
```

```bash
flask db upgrade
```

```bash
flask db migrate
```

## Performance testing (local synthetic volume)

Use this flow to stress the examiner ``GET /registrations/search`` path before and after API changes. All scripts read database credentials from [``.env``](.env) via the normal ``Development`` config (``DATABASE_HOST``, ``DATABASE_PORT``, ``DATABASE_NAME``, ``DATABASE_USERNAME``, ``DATABASE_PASSWORD``). If a comment in ``.env`` shows a different ``psql`` port than ``DATABASE_PORT``, use the same port Flask uses.

**Safety:** seeding refuses to run unless ``DEPLOYMENT_ENV`` is ``development``, ``dev``, ``local``, or ``sandbox``, or you pass ``--i-know-this-is-local``. Synthetic registration numbers start with ``PERF{seed}`` (for example ``PERF42``).

### 1. Seed large synthetic data

From the ``strr-api`` directory (after ``flask db upgrade``):

```bash
export DEPLOYMENT_ENV=development
make perf-seed
# or override volume: make perf-seed PERF_N=50000
# or: poetry run python scripts/perf_seed_registrations.py --registrations 20000 --batch-size 500 --seed 42
```

### 2. Refresh planner statistics

After a large insert, run ``ANALYZE`` so timings resemble production after stats refresh. With Homebrew ``libpq`` / ``psql``:

```bash
PGPASSWORD="$DATABASE_PASSWORD" psql -h "$DATABASE_HOST" -p "$DATABASE_PORT" \
  -U "$DATABASE_USERNAME" -d "$DATABASE_NAME" \
  -c "ANALYZE registrations; ANALYZE application; ANALYZE rental_properties; ANALYZE addresses; ANALYZE contacts; ANALYZE property_contacts;"
```

Record your Postgres version for reproducibility: ``psql ... -c 'SELECT version();'``.

### 3. HTTP baseline (in-process, no running Keycloak)

The benchmark uses JWT **test mode** (same keys as pytest) while still connecting to your local database from ``Development``.

```bash
export DEPLOYMENT_ENV=development
make perf-bench PERF_OUT=baseline-http.json
# or: poetry run python scripts/benchmark_registration_search.py --output baseline-http.json
```

Re-run after code changes with a different ``PERF_OUT`` and compare JSON (``median_ms`` per ``name``). For an apples-to-apples comparison, keep the same ``PERF_N`` and ``--seed`` when re-seeding, or restore a ``pg_dump`` snapshot taken immediately after the baseline seed.

Each JSON run also records ``perf_prefixed_registration_count`` (rows with ``registration_number`` like ``PERF%``) and whether ``STRR_REGISTRATION_SEARCH_SKIP_APPLICATION_BATCH`` was set.

### 3b. Before vs after (batched application load for search)

Examiner ``GET /registrations/search`` serializes each page of registrations. By default the API **batch-loads** all ``Application`` rows for those registration IDs in **one** query and returns a **lean list payload** (examiner table fields only: no snapshots, no conditions of approval, thin documents). The search query also **eager-loads** reviewers, properties, and related rows used by that payload. Set ``STRR_REGISTRATION_SEARCH_FULL_LIST_PAYLOAD=1`` to force the legacy full ``RegistrationSerializer.serialize`` shape for debugging or A/B comparisons.

To capture a **before** trace (legacy per-row queries), set ``STRR_REGISTRATION_SEARCH_SKIP_APPLICATION_BATCH=1`` for the benchmark process only:

```bash
mkdir -p perf_results
export DEPLOYMENT_ENV=development
STRR_REGISTRATION_SEARCH_SKIP_APPLICATION_BATCH=1 poetry run python scripts/benchmark_registration_search.py --iterations 7 --output perf_results/before.json
env -u STRR_REGISTRATION_SEARCH_SKIP_APPLICATION_BATCH poetry run python scripts/benchmark_registration_search.py --iterations 7 --output perf_results/after.json
poetry run python scripts/compare_perf_benchmarks.py --before perf_results/before.json --after perf_results/after.json --output perf_results/report.md
```

Or with Make: ``make perf-compare PERF_BEFORE=perf_results/before.json PERF_AFTER=perf_results/after.json PERF_REPORT=perf_results/report.md``.

Example write-up (methodology, table, interpretation): [docs/perf-registration-search-analysis.md](docs/perf-registration-search-analysis.md).

### 4. Capture SQL for ``EXPLAIN ANALYZE``

```bash
export DEPLOYMENT_ENV=development
make perf-sql PERF_CASE=requirement_pr 2>explain-capture.log
# or: poetry run python scripts/perf_sql_registration_search.py --case substatus_review_queue 2>explain-capture.log
```

Copy a ``SELECT`` or ``SELECT count(*)`` statement from the log into ``psql`` as ``EXPLAIN (ANALYZE, BUFFERS) ...`` and save the output (for example ``explain-baseline.txt``) next to your JSON baseline.

### 5. Optional cleanup

There is no automatic wipe. To remove synthetic rows, delete by prefix in dependency order (applications first), or restore a database snapshot taken before seeding.

## checking
You can pre-run the git hooks at the cmooand line
```bash
pre-commit run --all-files
```

## How to Contribute

If you would like to contribute, please see our [CONTRIBUTING](./CONTRIBUTING.md) guidelines.

Please note that this project is released with a [Contributor Code of Conduct](./CODE_OF_CONDUCT.md).
By participating in this project you agree to abide by its terms.

## License
Copyright © 2023 Province of British Columbia

Licensed under the BSD 3 Clause License, (the "License");
you may not use this file except in compliance with the License.
The template for the license can be found here
   https://opensource.org/license/bsd-3-clause/

Redistribution and use in source and binary forms,
with or without modification, are permitted provided that the
following conditions are met:

1. Redistributions of source code must retain the above copyright notice,
   this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its contributors
   may be used to endorse or promote products derived from this software
   without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS “AS IS”
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
