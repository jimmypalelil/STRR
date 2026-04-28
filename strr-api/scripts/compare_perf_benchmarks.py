#!/usr/bin/env python3
"""Compare two benchmark JSON files from ``benchmark_registration_search.py``.

Writes Markdown tables: per-scenario median delta, % change, and summary stats.

Example::

    poetry run python scripts/compare_perf_benchmarks.py \\
      --before perf_results/before.json --after perf_results/after.json \\
      --output perf_results/comparison.md
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=None, help="Write Markdown report here.")
    args = parser.parse_args()

    before = _load(args.before)
    after = _load(args.after)
    by_before = {r["name"]: r for r in before["results"]}
    by_after = {r["name"]: r for r in after["results"]}
    names = sorted(set(by_before) | set(by_after))

    rows: list[tuple] = []
    pct_deltas: list[float] = []
    for name in names:
        b = by_before.get(name)
        a = by_after.get(name)
        if not b or not a:
            rows.append((name, None, None, None, None, "missing in one input"))
            continue
        mb = float(b["median_ms"])
        ma = float(a["median_ms"])
        delta = ma - mb
        if mb > 0:
            pct = 100.0 * (ma - mb) / mb
            pct_deltas.append(pct)
        else:
            pct = 0.0 if ma == 0 else float("inf")
        faster = "after" if ma < mb else ("before" if ma > mb else "tie")
        rows.append((name, mb, ma, round(delta, 2), round(pct, 2), faster))

    lines: list[str] = []
    lines.append("# Registration search benchmark comparison\n")
    lines.append("## Run metadata\n")
    lines.append("| Field | Before | After |")
    lines.append("| --- | --- | --- |")
    lines.append(f"| recorded_at | `{before.get('recorded_at')}` | `{after.get('recorded_at')}` |")
    lines.append(f"| git_sha | `{before.get('git_sha')}` | `{after.get('git_sha')}` |")
    lines.append(
        f"| STRR_REGISTRATION_SEARCH_SKIP_APPLICATION_BATCH | `{before.get('strr_registration_search_skip_application_batch')}` | `{after.get('strr_registration_search_skip_application_batch')}` |"
    )
    lines.append(
        f"| perf_prefixed_registration_count | {before.get('perf_prefixed_registration_count')} | {after.get('perf_prefixed_registration_count')} |"
    )
    lines.append(f"| iterations_per_row | {before.get('iterations_per_row')} | {after.get('iterations_per_row')} |")
    lines.append("\n## Median latency by scenario\n")
    lines.append("| Scenario | Before median (ms) | After median (ms) | Delta (ms) | % change | Faster |")
    lines.append("| --- | ---: | ---: | ---: | ---: | --- |")
    for name, mb, ma, delta, pct, note in rows:
        if mb is None:
            lines.append(f"| {name} | — | — | — | — | {note} |")
        else:
            lines.append(f"| {name} | {mb} | {ma} | {delta} | {pct} | {note} |")

    lines.append("\n## Interpretation\n")
    if pct_deltas:
        mean_pct = statistics.mean(pct_deltas)
        lines.append(
            f"- **Mean % change across matched scenarios:** {mean_pct:.2f}% "
            f"(negative means faster after the change).\n"
        )
        wins_after = sum(1 for _, _, _, _, _, f in rows if f == "after")
        wins_before = sum(1 for _, _, _, _, _, f in rows if f == "before")
        lines.append(f"- **Scenarios faster after:** {wins_after} / **faster before:** {wins_before}.\n")
    lines.append(
        "- **Batch application load:** When `STRR_REGISTRATION_SEARCH_SKIP_APPLICATION_BATCH` is unset, "
        "`RegistrationService.search_registrations` loads all applications for the page in one query and "
        "passes them into `RegistrationSerializer`, avoiding up to three `Application.get_all_by_registration_id` "
        "calls per row.\n"
    )
    lines.append(
        "- Rows with **large response_bytes** (full page of HOST payloads) should show the largest improvement, "
        "because serialization dominates; filter-only rows returning empty lists may show little change.\n"
    )

    text = "\n".join(lines) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
        print(f"wrote {args.output}", flush=True)
    sys.stdout.write(text)


if __name__ == "__main__":
    main()
