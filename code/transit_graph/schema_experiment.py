import argparse
import csv
import json
import os
import statistics
import sys
import time
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
from transit_graph.schema import PlannerOutput
from transit_graph.workflow import build_graph


JSON_PATH = RAW_DIRECTORY / "schema_validation_runs.json"
CSV_PATH = RAW_DIRECTORY / "schema_validation_runs.csv"
SUMMARY_PATH = RAW_DIRECTORY / "schema_validation_summary.json"


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
        "run",
        "classification",
        "first_valid_attempt",
        "planner_attempts",
        "completed",
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


def classify(first_valid_attempt: int | None) -> str:
    if first_valid_attempt == 1:
        return "valid_first_attempt"

    if first_valid_attempt == 2:
        return "valid_after_one_retry"

    if first_valid_attempt is not None:
        return "valid_after_two_or_more_retries"

    return "abandoned_or_ceiling"


def run_once(
    run_number: int,
    case: dict[str, Any],
    client: OllamaModelClient,
    turn_ceiling: int
) -> dict[str, Any]:
    os.environ["TURN_CEILING"] = str(turn_ceiling)
    os.environ.pop("FORCE_REVIEW_ISSUE", None)

    graph = build_graph()

    initial_state = {
        "title": case["title"],
        "content": case["content"],
        "email": case["email"],
        "strict": case["strict"],
        "task": "",
        "llm": client,
        "planner_proposal": None,
        "reviewer_feedback": None,
        "turn_count": 0
    }

    final_state = dict(initial_state)
    planner_attempts = 0
    first_valid_attempt = None
    started = time.perf_counter()

    for update in graph.stream(
        initial_state,
        config={
            "recursion_limit": turn_ceiling * 3 + 10
        },
        stream_mode="updates"
    ):
        for node_name, node_update in update.items():
            if not isinstance(node_update, dict):
                continue

            final_state.update(node_update)

            if node_name != "planner":
                continue

            planner_attempts += 1
            proposal = node_update.get(
                "planner_proposal",
                {}
            )

            try:
                PlannerOutput.model_validate(proposal)

                if first_valid_attempt is None:
                    first_valid_attempt = planner_attempts
            except Exception:
                pass

    latency_ms = round(
        (time.perf_counter() - started) * 1000
    )

    proposal = final_state.get("planner_proposal") or {}
    review = final_state.get("reviewer_feedback") or {}

    completed = (
        first_valid_attempt is not None
        and review.get("approved") is True
    )

    return {
        "run": run_number,
        "classification": classify(first_valid_attempt),
        "first_valid_attempt": first_valid_attempt,
        "planner_attempts": planner_attempts,
        "completed": completed,
        "turn_count": final_state.get("turn_count", 0),
        "latency_ms": latency_ms,
        "tags": proposal.get("tags", []),
        "summary": proposal.get("summary", "")
    }


def create_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    categories = {
        "valid_first_attempt": 0,
        "valid_after_one_retry": 0,
        "valid_after_two_or_more_retries": 0,
        "abandoned_or_ceiling": 0
    }

    for result in results:
        category = result["classification"]
        categories[category] += 1

    mean_latency = round(
        statistics.mean(
            result["latency_ms"]
            for result in results
        ),
        2
    )

    completed = sum(
        result["completed"]
        for result in results
    )

    return {
        "total_runs": len(results),
        "categories": categories,
        "completed_runs": completed,
        "completion_rate_percent": round(
            completed / len(results) * 100,
            2
        ),
        "mean_latency_ms": mean_latency
    }


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
        default=30
    )
    parser.add_argument(
        "--turn-ceiling",
        type=int,
        default=10
    )
    arguments = parser.parse_args()

    input_path = ROOT / arguments.input
    case = json.loads(
        input_path.read_text(encoding="utf-8")
    )

    results = load_results()
    completed_runs = len(results)

    print(
        f"Resuming from {completed_runs} completed runs."
    )

    client = OllamaModelClient(
        model=arguments.model,
        temperature=arguments.temperature
    )

    for run_number in range(
        completed_runs + 1,
        arguments.runs + 1
    ):
        result = run_once(
            run_number,
            case,
            client,
            arguments.turn_ceiling
        )

        results.append(result)
        save_results(results)

        print(
            f"Run {run_number}/{arguments.runs}: "
            f"{result['classification']}, "
            f"{result['latency_ms']} ms"
        )

    summary = create_summary(results)

    SUMMARY_PATH.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8"
    )

    print("\n--- Schema Validation Summary ---")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()