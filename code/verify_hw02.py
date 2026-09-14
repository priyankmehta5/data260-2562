import json
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GRAPH_DIR = ROOT / "code" / "transit_graph"
OUTPUT = ROOT / "reports" / "hw02" / "verification.json"

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(GRAPH_DIR))

from schema_experiment import run_once
from src.model_client import OllamaModelClient


def result(name, passed, details):
    return {
        "name": name,
        "passed": bool(passed),
        "details": details
    }


def count_json(relative_path):
    path = ROOT / relative_path

    if not path.is_file():
        return 0

    data = json.loads(path.read_text(encoding="utf-8"))
    return len(data) if isinstance(data, list) else 0


def test_api():
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "code.api.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8762"
        ],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    try:
        for _ in range(30):
            try:
                with urllib.request.urlopen(
                    "http://127.0.0.1:8762/api/incidents",
                    timeout=2
                ) as response:
                    data = json.loads(response.read())

                    passed = (
                        response.status == 200
                        and isinstance(data, list)
                    )

                    return result(
                        "FastAPI responds on PORT_BASE",
                        passed,
                        (
                            f"HTTP {response.status}; "
                            f"{len(data)} incident records returned"
                        )
                    )
            except Exception:
                time.sleep(0.5)

        return result(
            "FastAPI responds on PORT_BASE",
            False,
            "API did not respond on port 8762"
        )
    finally:
        process.terminate()

        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


def test_graph():
    case = {
        "title": "VTA Blue Line Signal Failure",
        "content": (
            "A signal failure near Santa Clara station caused "
            "major delays and disrupted Blue Line light rail "
            "service during the morning commute."
        ),
        "email": "priyank.mehta@sjsu.edu",
        "strict": True
    }

    client = OllamaModelClient(
        model="qwen3:1.7b",
        temperature=0.0
    )

    try:
        graph_result = run_once(
            1,
            case,
            client,
            10
        )

        tags = graph_result.get("tags", [])
        summary = graph_result.get("summary", "")
        completed = graph_result.get("completed", False)

        passed = (
            completed
            and isinstance(tags, list)
            and len(tags) == 3
            and all(
                isinstance(tag, str)
                and 3 <= len(tag.strip()) <= 30
                for tag in tags
            )
            and 0 < len(summary.split()) <= 25
        )

        return result(
            "LangGraph completes with valid schema",
            passed,
            (
                f"completed={completed}; "
                f"tag_count={len(tags)}; "
                f"summary_words={len(summary.split())}; "
                f"turn_count={graph_result.get('turn_count')}"
            )
        )
    except Exception as error:
        return result(
            "LangGraph completes with valid schema",
            False,
            f"{type(error).__name__}: {error}"
        )


def main():
    commit_hash = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True
    ).strip()

    schema_count = count_json(
        "reports/hw02/raw/schema_validation_runs.json"
    )
    ceiling_count = count_json(
        "reports/hw02/raw/ceiling_comparison_runs.json"
    )
    adversarial_count = count_json(
        "reports/hw02/raw/adversarial_runs.json"
    )

    checks = [
        test_api(),
        test_graph(),
        result(
            "Schema-validation run count",
            schema_count == 30,
            f"Expected 30; found {schema_count}"
        ),
        result(
            "Ceiling-comparison run count",
            ceiling_count == 40,
            f"Expected 40; found {ceiling_count}"
        ),
        result(
            "Adversarial run count",
            adversarial_count == 5,
            f"Expected 5; found {adversarial_count}"
        )
    ]

    verification = {
        "homework_number": 2,
        "sid4": 2562,
        "commit_hash": commit_hash,
        "model_configuration": {
            "model": "qwen3:1.7b",
            "temperature": 0.0,
            "num_ctx": 4096,
            "execution": "CPU-only",
            "port_base": 8762
        },
        "seed": 2562,
        "verify_seed": 262562,
        "verified_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "checks": checks,
        "overall_passed": all(
            check["passed"] for check in checks
        )
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(verification, indent=2),
        encoding="utf-8"
    )

    print(json.dumps(verification, indent=2))


if __name__ == "__main__":
    main()
