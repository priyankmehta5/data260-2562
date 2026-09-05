import argparse
import csv
import json
import math
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AGENT_SCRIPT = ROOT / "code" / "agents_demo.py"
RAW_DIRECTORY = ROOT / "reports" / "hw01" / "raw"
RUNS_JSON = RAW_DIRECTORY / "nondeterminism_runs.json"
RUNS_CSV = RAW_DIRECTORY / "nondeterminism_runs.csv"
SUMMARY_JSON = RAW_DIRECTORY / "nondeterminism_summary.json"


def percentile(values, percent):
    ordered = sorted(values)
    position = (len(ordered) - 1) * percent / 100
    lower = math.floor(position)
    upper = math.ceil(position)

    if lower == upper:
        return ordered[lower]

    fraction = position - lower
    return ordered[lower] + (
        ordered[upper] - ordered[lower]
    ) * fraction


def load_results():
    if not RUNS_JSON.exists():
        return []

    with RUNS_JSON.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_results(results):
    RAW_DIRECTORY.mkdir(parents=True, exist_ok=True)

    with RUNS_JSON.open("w", encoding="utf-8") as file:
        json.dump(results, file, indent=2)

    with RUNS_CSV.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "temperature",
                "run_number",
                "tags",
                "summary",
                "latency_ms",
                "timestamp_utc",
            ],
        )
        writer.writeheader()

        for result in results:
            writer.writerow(
                {
                    **result,
                    "tags": json.dumps(result["tags"]),
                }
            )


def extract_finalized_output(stdout):
    start_marker = "--- Finalized Output ---"
    end_marker = "--- Publish Output ---"

    start = stdout.find(start_marker)
    end = stdout.find(end_marker)

    if start == -1 or end == -1:
        raise ValueError("Finalized output was not found.")

    json_text = stdout[start + len(start_marker):end].strip()
    result = json.loads(json_text)

    if len(result.get("tags", [])) != 3:
        raise ValueError("The run did not produce exactly three tags.")

    if len(result.get("summary", "").split()) > 25:
        raise ValueError("The summary exceeded 25 words.")

    return result


def run_pipeline(title, content, model, temperature):
    command = [
        sys.executable,
        str(AGENT_SCRIPT),
        "--title",
        title,
        "--content",
        content,
        "--model",
        model,
        "--temperature",
        str(temperature),
        "--strict",
    ]

    started = time.perf_counter()

    completed = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )

    latency_ms = round(
        (time.perf_counter() - started) * 1000
    )

    return extract_finalized_output(completed.stdout), latency_ms


def summarize_temperature(results, temperature):
    selected = [
        result
        for result in results
        if result["temperature"] == temperature
    ]

    tag_sets = {
        tuple(sorted(set(result["tags"])))
        for result in selected
    }

    tag_counts = Counter()

    for result in selected:
        tag_counts.update(set(result["tags"]))

    common_tags = sorted(
        tag
        for tag, count in tag_counts.items()
        if count == len(selected)
    )

    single_run_tags = sorted(
        tag
        for tag, count in tag_counts.items()
        if count == 1
    )

    latencies = [
        result["latency_ms"]
        for result in selected
    ]

    return {
        "temperature": temperature,
        "successful_runs": len(selected),
        "distinct_tag_sets": len(tag_sets),
        "tags_in_all_runs": common_tags,
        "tags_in_exactly_one_run": single_run_tags,
        "latency_ms": {
            "p50": round(percentile(latencies, 50)),
            "p95": round(percentile(latencies, 95)),
            "p99": round(percentile(latencies, 99)),
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default=(
            "reports/hw01/cases/"
            "nondeterminism_input.json"
        ),
    )
    parser.add_argument(
        "--model",
        default="qwen3:1.7b",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=20,
    )
    args = parser.parse_args()

    input_path = ROOT / args.input

    with input_path.open("r", encoding="utf-8") as file:
        case = json.load(file)

    results = load_results()
    temperatures = [0.7, 0.0]

    for temperature in temperatures:
        completed_runs = sum(
            1
            for result in results
            if result["temperature"] == temperature
        )

        for run_number in range(
            completed_runs + 1,
            args.runs + 1,
        ):
            print(
                f"Temperature {temperature}, "
                f"run {run_number}/{args.runs}"
            )

            final, latency_ms = run_pipeline(
                case["title"],
                case["content"],
                args.model,
                temperature,
            )

            result = {
                "temperature": temperature,
                "run_number": run_number,
                "tags": final["tags"],
                "summary": final["summary"],
                "latency_ms": latency_ms,
                "timestamp_utc": datetime.now(
                    timezone.utc
                ).isoformat(),
            }

            results.append(result)
            save_results(results)

            print(
                json.dumps(
                    {
                        "tags": result["tags"],
                        "latency_ms": latency_ms,
                    },
                    indent=2,
                )
            )

    summaries = [
        summarize_temperature(results, temperature)
        for temperature in temperatures
    ]

    with SUMMARY_JSON.open("w", encoding="utf-8") as file:
        json.dump(summaries, file, indent=2)

    print("\nExperiment complete")
    print(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    main()