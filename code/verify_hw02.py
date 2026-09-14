"""Generate reports/hw02/verification.json using objective smoke tests."""

from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
GRAPH_DIR = ROOT / "code" / "transit_graph"
REPORT_DIR = ROOT / "reports" / "hw02"
OUTPUT_PATH = REPORT_DIR / "verification.json"

HOMEWORK_NUMBER = 2
SID4 = 2562
SEED = 2562
VERIFY_SEED = 262562
PORT_BASE = 8762

MODEL_NAME = "qwen3:1.7b"
TEMPERATURE = 0.0
NUM_CTX = 4096

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if str(GRAPH_DIR) not in sys.path:
    sys.path.insert(0, str(GRAPH_DIR))

from schema_experiment import run_once
from src.model_client import OllamaModelClient


def git_commit_hash() -> str:
    """Return the full hash of the currently checked-out commit."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def add_check(
    checks: list[dict[str, Any]],
    name: str,
    passed: bool,
    details: str,
) -> None:
    """Add one verification result."""
    checks.append(
        {
            "name": name,
            "passed": bool(passed),
            "details": details,
        }
    )


def stop_process(process: subprocess.Popen[Any]) -> None:
    """Stop the temporary API process without modifying application files."""
    if process.poll() is not None:
        return

    process.terminate()

    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def check_api(checks: list[dict[str, Any]]) -> None:
    """Start FastAPI and confirm that its incidents endpoint responds."""
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "main:app",
        "--app-dir",
        str(ROOT / "code" / "api"),
        "--host",
        "127.0.0.1",
        "--port",
        str(PORT_BASE),
    ]

    process = subprocess.Popen(
        command,
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    url = f"http://127.0.0.1:{PORT_BASE}/api/incidents"
    last_error = "API did not respond"

    try:
        for _ in range(30):
            if process.poll() is not None:
                last_error = (
                    "Uvicorn exited before the API became available "
                    f"with exit code {process.returncode}"
                )
                break

            try:
                with urllib.request.urlopen(url, timeout=2) as response:
                    body = response.read()
                    status = response.status

                parsed = json.loads(body.decode("utf-8"))
                passed = status == 200

                add_check(
                    checks,
                    "FastAPI responds on PORT_BASE",
                    passed,
                    (
                        f"GET {url} returned HTTP {status}; "
                        f"JSON type={type(parsed).__name__}"
                    ),
                )
                return
            except (
                urllib.error.URLError,
                TimeoutError,
                ConnectionError,
                json.JSONDecodeError,
            ) as error:
                last_error = str(error)
                time.sleep(1)

        add_check(
            checks,
            "FastAPI responds on PORT_BASE",
            False,
            f"API did not respond on port {PORT_BASE}: {last_error}",
        )
    finally:
        stop_process(process)


def word_count(value: str) -> int:
    """Count non-empty whitespace-separated words."""
    return len([word for word in value.split() if word])


def check_langgraph(checks: list[dict[str, Any]]) -> None:
    """Run one LangGraph case and validate behavior instead of exact wording."""
    case_path = (
        ROOT
        / "reports"
        / "hw02"
        / "cases"
        / "schema_input.json"
    )

    with case_path.open("r", encoding="utf-8") as file:
        case = json.load(file)

    try:
        client = OllamaModelClient(
            model=MODEL_NAME,
            temperature=TEMPERATURE,
            num_ctx=NUM_CTX,
        )

        result = run_once(
            1,
            case,
            client,
            10,
        )

        completed = bool(result.get("completed"))
        tags = result.get("tags", [])
        summary = str(result.get("summary", "")).strip()
        turns = result.get("turn_count")

        tag_count_valid = (
            isinstance(tags, list)
            and len(tags) == 3
        )

        tag_lengths_valid = (
            isinstance(tags, list)
            and all(
                isinstance(tag, str)
                and 3 <= len(tag.strip()) <= 30
                for tag in tags
            )
        )

        summary_words = word_count(summary)
        summary_valid = 1 <= summary_words <= 25

        passed = (
            completed
            and tag_count_valid
            and tag_lengths_valid
            and summary_valid
        )

        add_check(
            checks,
            "LangGraph completes with valid schema",
            passed,
            (
                f"completed={completed}; "
                f"tag_count={len(tags) if isinstance(tags, list) else 0}; "
                f"summary_words={summary_words}; "
                f"turn_count={turns}"
            ),
        )
    except Exception as error:
        add_check(
            checks,
            "LangGraph completes with valid schema",
            False,
            f"{type(error).__name__}: {error}",
        )


def load_record_count(path: Path) -> int:
    """Return the number of experiment records in a JSON file."""
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, list):
        return len(data)

    if isinstance(data, dict):
        for key in ("runs", "results", "records"):
            records = data.get(key)
            if isinstance(records, list):
                return len(records)

    raise ValueError(f"Could not find a record list in {path}")


def check_run_count(
    checks: list[dict[str, Any]],
    name: str,
    relative_path: str,
    expected: int,
) -> None:
    """Check that a saved experiment contains the expected number of runs."""
    path = ROOT / relative_path

    try:
        found = load_record_count(path)
        add_check(
            checks,
            name,
            found == expected,
            f"Expected {expected}; found {found}",
        )
    except Exception as error:
        add_check(
            checks,
            name,
            False,
            f"{type(error).__name__}: {error}",
        )


def main() -> int:
    """Run all checks and write the required verification artifact."""
    checks: list[dict[str, Any]] = []

    check_api(checks)
    check_langgraph(checks)

    check_run_count(
        checks,
        "Schema-validation run count",
        "reports/hw02/raw/schema_validation_runs.json",
        30,
    )

    check_run_count(
        checks,
        "Ceiling-comparison run count",
        "reports/hw02/raw/ceiling_comparison_runs.json",
        40,
    )

    check_run_count(
        checks,
        "Adversarial run count",
        "reports/hw02/raw/adversarial_runs.json",
        5,
    )

    verification = {
        "homework_number": HOMEWORK_NUMBER,
        "sid4": SID4,
        "commit_hash": git_commit_hash(),
        "model_configuration": {
            "model": MODEL_NAME,
            "temperature": TEMPERATURE,
            "num_ctx": NUM_CTX,
            "execution": "CPU-only",
            "port_base": PORT_BASE,
        },
        "seed": SEED,
        "verify_seed": VERIFY_SEED,
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "overall_passed": all(
            check["passed"] for check in checks
        ),
    }

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(verification, indent=2) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(verification, indent=2))
    return 0 if verification["overall_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())