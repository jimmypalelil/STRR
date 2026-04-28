# Examiner registration search: before/after analysis (batched application load)

This document records controlled **before vs after** benchmarks for `GET /registrations/search`, using the harness under [`scripts/`](../scripts/) and the batched-application serialization optimization.

## What changed (after)

1. **`Application.get_all_by_registration_ids`** ([`application.py`](../src/strr_api/models/application.py)) loads all applications for a list of registration IDs in **one** round-trip, grouped and sorted by `application_date` descending per registration.

2. **`RegistrationSerializer.serialize`** accepts optional `applications`. When provided, `_populate_applications`, `get_jurisdiction_from_application`, and `get_str_requirements_from_application` reuse that list instead of calling `Application.get_all_by_registration_id` up to **three times per registration**.

3. **`RegistrationService.search_registrations`** and the **paginated user registration list** batch-load applications for the current page, then pass each list into `serialize`.

4. **Benchmarking only:** `STRR_REGISTRATION_SEARCH_SKIP_APPLICATION_BATCH=1` forces the legacy per-row application queries for A/B timing without a second branch.

## Methodology

| Step | Action |
| --- | --- |
| Dataset | Synthetic `PERF*` rows from [`scripts/perf_seed_registrations.py`](../scripts/perf_seed_registrations.py); `perf_prefixed_registration_count` in each JSON is `SELECT count(*) … WHERE registration_number LIKE 'PERF%'`. |
| DB stats | `ANALYZE` on `registrations`, `application`, `rental_properties`, `addresses`, `contacts`, `property_contacts` after seeding. |
| HTTP driver | [`scripts/benchmark_registration_search.py`](../scripts/benchmark_registration_search.py): Flask **test client**, JWT **test mode**, `UserService.get_or_create_user_by_jwt` patched. |
| Iterations | **10** samples per matrix row (medians below). |
| Matrix | Same as examiner-style filters: default registration statuses, sub-status, `reviewRenew`, requirements, `localGov`, `text`, `registrationType`, `nocStatus`, combined. |
| Comparison | [`scripts/compare_perf_benchmarks.py`](../scripts/compare_perf_benchmarks.py) or `make perf-compare`. |

---

## Serious dataset run (15k new synthetic rows)

### Environment

| Item | Value |
| --- | --- |
| Seed command | `poetry run python scripts/perf_seed_registrations.py --registrations 15000 --batch-size 500 --seed 99` |
| `PERF*` registration count | **15,003** (15,000 with prefix `PERF99` plus three earlier local `PERF*` smoke rows) |
| PostgreSQL | **16.13**, `aarch64-unknown-linux-musl` (Alpine toolchain), observed via `SELECT version()` |
| Host | Local dev DB reached from `Development` config (same machine as API process). |

### Run metadata

| Field | Before | After |
| --- | --- | --- |
| `recorded_at` | `2026-04-28T23:47:00.267609+00:00` | `2026-04-28T23:47:36.420992+00:00` |
| `git_sha` | `34b337bf` | `34b337bf` |
| `STRR_REGISTRATION_SEARCH_SKIP_APPLICATION_BATCH` | `1` | unset |
| `perf_prefixed_registration_count` | 15003 | 15003 |
| `iterations_per_row` | 10 | 10 |

### Median latency by scenario (ms)

| Scenario | Before | After | Delta | % change | Faster |
| --- | ---: | ---: | ---: | ---: | --- |
| default_statuses_only | 300.31 | 276.94 | -23.37 | -7.78 | after |
| substatus_review_queue | 320.30 | 264.24 | -56.06 | -17.50 | after |
| substatus_review_renew | 10.10 | 9.87 | -0.23 | -2.28 | after |
| requirement_pr | 310.02 | 260.60 | -49.42 | -15.94 | after |
| requirement_pr_and_bl | 315.41 | 260.97 | -54.44 | -17.26 | after |
| localgov_maple | 308.04 | 259.47 | -48.57 | -15.77 | after |
| text_search | 303.26 | 256.95 | -46.31 | -15.27 | after |
| registration_type_host | 302.80 | 254.51 | -48.29 | -15.95 | after |
| noc_pending | 316.66 | 266.78 | -49.88 | -15.75 | after |
| combined_pr_localgov | 324.30 | 270.30 | -54.00 | -16.65 | after |

**Summary:** mean of per-scenario % changes ≈ **-14.0%**; **10 / 10** scenarios faster after batching.

### Interpretation (serious run)

1. **Consistent wins on filter paths that still return a full page (~180 KB JSON)**  
   Requirement, sub-status, NOC, `localGov`, and combined filters all spend hundreds of milliseconds in the **before** path. Removing up to **150 × 3** extra `Application` round-trips per request (50 rows × three fetches per row in the worst legacy case) shows up as roughly **15–17%** median reduction for those scenarios—aligned with DB + Python time dominated by list serialization and related lazy loads.

2. **`default_statuses_only` improves less (~8%)**  
   Same page size (~181 KB), but the SQL filter is a simple `status IN (…)` without correlated subqueries from sub-status or requirement filters, so total time is slightly lower and the **fraction** of time spent in redundant application queries is smaller; batching still helps but shows a smaller relative delta.

3. **`substatus_review_renew` stays fast with a small relative delta**  
   The query returns almost no rows (~68 B response in the micro run; still small here). Median latency is ~10 ms; the optimization removes only a sliver of work, so **-2.3%** is expected noise-level improvement.

4. **Still not “production”**  
   This is synthetic data, single-machine Postgres, in-process Flask (no real Keycloak, no network hop to a separate API tier). Use these numbers for **regression direction and magnitude**, not SLA guarantees.

### SQL scope (unchanged)

Batched applications do **not** change the main `Registration.search_registrations` filter SQL or the pagination `COUNT`. Further gains on the heaviest filters require planner/index or denormalization work as a separate effort.

---

## Micro-dataset (3 `PERF*` rows, earlier smoke)

With only three rows, several matrix rows returned empty 68-byte bodies and timings were noise-dominated; full-page rows still showed ~9–14% improvement. That run is superseded by the **15k** table above for decision-making.

---

## How to reproduce

```bash
cd strr-api
export DEPLOYMENT_ENV=development

# Load volume (tune N)
poetry run python scripts/perf_seed_registrations.py --registrations 15000 --batch-size 500 --seed 99

# ANALYZE (see README for psql one-liner, or use a small SQLAlchemy script)

STRR_REGISTRATION_SEARCH_SKIP_APPLICATION_BATCH=1 \
  poetry run python scripts/benchmark_registration_search.py --iterations 10 --output perf_results/serious-before.json

env -u STRR_REGISTRATION_SEARCH_SKIP_APPLICATION_BATCH \
  poetry run python scripts/benchmark_registration_search.py --iterations 10 --output perf_results/serious-after.json

poetry run python scripts/compare_perf_benchmarks.py \
  --before perf_results/serious-before.json --after perf_results/serious-after.json --output perf_results/serious-comparison.md
```

`strr-api/perf_results/` is gitignored; this file is the durable record.

## Suggested next steps

1. Scale to **50k+** `PERF*` rows if you need confidence in tail latency and buffer cache behavior.
2. Capture `EXPLAIN (ANALYZE, BUFFERS)` for the slowest **SQL-only** filters separately from serializer work.
3. Optional: add a `RUN_PERF=1` CI job that runs the benchmark matrix against a migrated test DB with a modest fixed N (see plan “optional hardening”).
