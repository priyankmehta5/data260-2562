import argparse
import csv
import json
import statistics
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CODE_DIRECTORY = ROOT / "code"
RAW_DIRECTORY = ROOT / "reports" / "hw02" / "raw"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if str(CODE_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(CODE_DIRECTORY))

from src.model_client import OllamaModelClient
from transit_graph.schema_experiment import run_once


JSON_PATH = RAW_DIRECTORY / "ceiling_comparison_runs.json"
CSV_PATH = RAW_DIRECTORY / "ceiling_comparison_runs.csv"
SUMMARY_PATH = RAW_DIRECTORY / "ceiling_comparison_summary.json"


def load_results() -> list[dict[str, Any]]:
    if not JSON_PATH.exists():
        return []

    try:
        return json.loads(
            JSON_PATH.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError:
        return []


def save_results(results: list[dict[str, Any]]) -> None:
    RAW_DIRECTORY.mkdir(parents=True, exist_ok=True)

    JSON_PATH.write_text(
        json.dumps(results, indent=2),
        encoding="utf-8"
    )

    fields = [
        "turn_ceiling",
        "run",
        "completed",
        "classification",
        "first_valid_attempt",
        "planner_attempts",
        "turn_count",
        "latency_ms",
        "tags",
        "summary"
    ]

    with CSV_PATH.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()

        for result in results:
            row = {
                field: result.get(field, "")
                for field in fields
            }
            row["tags"] = json.dumps(result.get("tags", []))
            writer.writerow(row)


def create_summary(
    results: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    summary = []

    for ceiling in [2, 10]:
        ceiling_results = [
            result
            for result in results
            if result["turn_ceiling"] == ceiling
        ]

        completed = sum(
            result["completed"]
            for result in ceiling_results
        )

        mean_latency = round(
            statistics.mean(
                result["latency_ms"]
                for result in ceiling_results
            ),
            2
        )

        summary.append(
            {
                "turn_ceiling": ceiling,
                "total_runs": len(ceiling_results),
                "completed_runs": completed,
                "completion_rate_percent": round(
                    completed
                    / len(ceiling_results)
                    * 100,
                    2
                ),
                "mean_latency_ms": mean_latency
            }
        )

    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="reports/hw02/cases/schema_input.json"
    )
    parser.add_argument(
        "--model",
        default="qwen3:1.7b"
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=20
    )
    arguments = parser.parse_args()

    case = json.loads(
        (ROOT / arguments.input).read_text(
            encoding="utf-8"
        )
    )

    results = load_results()

    client = OllamaModelClient(
        model=arguments.model,
        temperature=arguments.temperature
    )

    for ceiling in [2, 10]:
        completed_for_ceiling = sum(
            result["turn_ceiling"] == ceiling
            for result in results
        )

        print(
            f"Ceiling {ceiling}: resuming from "
            f"{completed_for_ceiling} completed runs."
        )

        for run_number in range(
            completed_for_ceiling + 1,
            arguments.runs + 1
        ):
            result = run_once(
                run_number,
                case,
                client,
                ceiling
            )

            result["turn_ceiling"] = ceiling
            results.append(result)
            save_results(results)

            print(
                f"Ceiling {ceiling}, "
                f"run {run_number}/{arguments.runs}: "
                f"completed={result['completed']}, "
                f"{result['latency_ms']} ms"
            )

    summary = create_summary(results)

    SUMMARY_PATH.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8"
    )

    print("\n--- Turn Ceiling Comparison ---")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()