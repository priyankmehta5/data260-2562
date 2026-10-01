import csv
import json
import random
import time
from collections import defaultdict
from pathlib import Path


import requests


BASE_URL = "http://localhost:8762"
VERIFY_SEED = 262562
PAGE_SIZES = [10, 50, 200]
RUNS_PER_CONFIGURATION = 30

ROOT = Path(__file__).resolve().parents[2]
RAW_DIRECTORY = ROOT / "reports" / "hw04" / "raw"
RAW_DIRECTORY.mkdir(parents=True, exist_ok=True)

RAW_CSV = RAW_DIRECTORY / "n_plus_one_requests.csv"
SUMMARY_JSON = RAW_DIRECTORY / "n_plus_one_summary.json"
METRICS_MD = ROOT / "reports" / "hw04" / "METRICS.md"


def percentile(values, percentage):
    ordered = sorted(values)

    if len(ordered) == 1:
        return ordered[0]

    position = (len(ordered) - 1) * percentage
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower

    return (
        ordered[lower]
        + (ordered[upper] - ordered[lower]) * fraction
    )


def main():
    session = requests.Session()

    login_response = session.post(
        f"{BASE_URL}/api/login",
        json={
            "email": "student@example.com",
            "password": "Transit2562!",
        },
        timeout=30,
    )
    login_response.raise_for_status()

    configurations = []

    for version in ["naive", "optimized"]:
        for page_size in PAGE_SIZES:
            for run_number in range(
                1,
                RUNS_PER_CONFIGURATION + 1,
            ):
                configurations.append(
                    {
                        "version": version,
                        "page_size": page_size,
                        "run_number": run_number,
                    }
                )

    random.Random(VERIFY_SEED).shuffle(configurations)

    results = []

    for request_number, configuration in enumerate(
        configurations,
        start=1,
    ):
        version = configuration["version"]
        page_size = configuration["page_size"]

        endpoint = (
            f"/api/performance/incidents-{version}"
        )

        started = time.perf_counter()

        response = session.get(
            f"{BASE_URL}{endpoint}",
            params={"page_size": page_size},
            timeout=60,
        )

        end_to_end_ms = (
            time.perf_counter() - started
        ) * 1000

        response.raise_for_status()
        payload = response.json()

        result = {
            "request_number": request_number,
            "run_number": configuration["run_number"],
            "version": version,
            "page_size": page_size,
            "status_code": response.status_code,
            "sql_queries": payload["sql_queries"],
            "server_retrieval_ms": payload[
                "retrieval_latency_ms"
            ],
            "end_to_end_ms": round(end_to_end_ms, 3),
            "record_count": len(payload["records"]),
        }

        results.append(result)

        print(
            f"{request_number:03d}/180 "
            f"{version:9s} "
            f"page_size={page_size:3d} "
            f"queries={result['sql_queries']:3d} "
            f"latency={result['end_to_end_ms']:.3f} ms"
        )

    with RAW_CSV.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as output_file:
        writer = csv.DictWriter(
            output_file,
            fieldnames=results[0].keys(),
        )
        writer.writeheader()
        writer.writerows(results)

    grouped = defaultdict(list)

    for result in results:
        key = (
            result["version"],
            result["page_size"],
        )
        grouped[key].append(result)

    summary = []

    for version in ["naive", "optimized"]:
        for page_size in PAGE_SIZES:
            group = grouped[(version, page_size)]
            latencies = [
                row["end_to_end_ms"]
                for row in group
            ]

            summary.append(
                {
                    "version": version,
                    "page_size": page_size,
                    "request_count": len(group),
                    "sql_queries_per_request": group[0][
                        "sql_queries"
                    ],
                    "p50_ms": round(
                        percentile(latencies, 0.50),
                        3,
                    ),
                    "p95_ms": round(
                        percentile(latencies, 0.95),
                        3,
                    ),
                    "p99_ms": round(
                        percentile(latencies, 0.99),
                        3,
                    ),
                }
            )

    for page_size in PAGE_SIZES:
        naive = next(
            row
            for row in summary
            if row["version"] == "naive"
            and row["page_size"] == page_size
        )
        optimized = next(
            row
            for row in summary
            if row["version"] == "optimized"
            and row["page_size"] == page_size
        )

        optimized["p50_speedup"] = round(
            naive["p50_ms"] / optimized["p50_ms"],
            2,
        )

    SUMMARY_JSON.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    lines = [
        "# HW4 N+1 Metrics",
        "",
        f"- VERIFY_SEED: {VERIFY_SEED}",
        f"- Total requests: {len(results)}",
        "",
        "| Version | Page size | SQL statements/request | p50 (ms) | p95 (ms) | p99 (ms) | p50 speedup |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]

    for row in summary:
        speedup = row.get("p50_speedup", "-")

        lines.append(
            f"| {row['version']} "
            f"| {row['page_size']} "
            f"| {row['sql_queries_per_request']} "
            f"| {row['p50_ms']} "
            f"| {row['p95_ms']} "
            f"| {row['p99_ms']} "
            f"| {speedup} |"
        )

    METRICS_MD.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    print("\nBenchmark complete.")
    print(f"Total requests: {len(results)}")
    print(f"Raw results: {RAW_CSV}")
    print(f"Summary: {SUMMARY_JSON}")
    print(f"Metrics: {METRICS_MD}")

    print("\nSummary:")
    for row in summary:
        print(row)


if __name__ == "__main__":
    main()