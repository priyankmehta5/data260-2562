import ast
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "reports" / "hw01" / "verification.json"
VERIFY_SEED = 262562

checks = []


def record(name, passed, details):
    checks.append({
        "name": name,
        "status": "PASS" if passed else "FAIL",
        "details": details
    })


required_files = [
    "AGENT.md",
    "DOMAIN_SCHEMA.md",
    "README.md",
    "requirements.txt",
    "code/Dockerfile",
    "code/agents_demo.py",
    "code/hw1_client.py",
    "code/run_nondeterminism.py",
    "code/web_application/index.html",
    "code/web_application/script.js",
    "src/model_client.py",
    "reports/hw01/AI_USE.md",
    "reports/hw01/METRICS.md",
    "reports/hw01/RUN_LOG.txt",
    "reports/hw01/reproducible_run_instructions",
    "reports/hw01/cases/nondeterminism_input.json",
    "reports/hw01/raw/nondeterminism_runs.json",
    "reports/hw01/raw/nondeterminism_runs.csv",
    "reports/hw01/raw/nondeterminism_summary.json",
    "reports/hw01/raw/part4_transcript.txt"
]

missing_files = [
    path for path in required_files
    if not (ROOT / path).is_file()
]

record(
    "required_files",
    not missing_files,
    "All required files exist"
    if not missing_files
    else f"Missing files: {missing_files}"
)

html_path = ROOT / "code" / "web_application" / "index.html"
if html_path.is_file():
    html = html_path.read_text(encoding="utf-8").lower()
    record(
        "html_title",
        "<title>hw1-" in html,
        "HTML title begins with HW1-"
    )
else:
    record("html_title", False, "index.html was not found")

try:
    with urllib.request.urlopen(
        "http://localhost:8762",
        timeout=10
    ) as response:
        page = response.read().decode("utf-8", errors="replace")
        passed = response.status == 200 and "<title>hw1-" in page.lower()
        record(
            "docker_web_application",
            passed,
            f"HTTP status: {response.status}"
        )
except Exception as error:
    record(
        "docker_web_application",
        False,
        f"Application unavailable: {error}"
    )

model_client_path = ROOT / "src" / "model_client.py"
if model_client_path.is_file():
    tree = ast.parse(model_client_path.read_text(encoding="utf-8"))
    complete_found = any(
        isinstance(node, ast.FunctionDef) and node.name == "complete"
        for node in ast.walk(tree)
    )
    record(
        "model_adapter_interface",
        complete_found,
        "complete(messages, tools=None) method found"
        if complete_found
        else "complete method was not found"
    )
else:
    record(
        "model_adapter_interface",
        False,
        "src/model_client.py was not found"
    )

runs_path = (
    ROOT / "reports" / "hw01" / "raw"
    / "nondeterminism_runs.json"
)

try:
    runs = json.loads(runs_path.read_text(encoding="utf-8"))
    temperature_07 = sum(
        run.get("temperature") == 0.7 for run in runs
    )
    temperature_00 = sum(
        run.get("temperature") == 0.0 for run in runs
    )

    record(
        "nondeterminism_run_count",
        len(runs) == 40,
        f"Total runs: {len(runs)}"
    )
    record(
        "temperature_0.7_run_count",
        temperature_07 == 20,
        f"Temperature 0.7 runs: {temperature_07}"
    )
    record(
        "temperature_0.0_run_count",
        temperature_00 == 20,
        f"Temperature 0.0 runs: {temperature_00}"
    )

    valid_outputs = all(
        len(run.get("tags", [])) == 3
        and len(run.get("summary", "").split()) <= 25
        and run.get("latency_ms", 0) > 0
        for run in runs
    )

    record(
        "nondeterminism_output_format",
        valid_outputs,
        "Every run has three tags, a summary of at most 25 words, and positive latency"
    )
except Exception as error:
    record(
        "nondeterminism_results",
        False,
        f"Could not validate results: {error}"
    )

transcript_path = (
    ROOT / "reports" / "hw01" / "raw"
    / "part4_transcript.txt"
)

if transcript_path.is_file():
    transcript = transcript_path.read_text(
        encoding="utf-8",
        errors="replace"
    )
    transcript_valid = (
        "Turn count: 5" in transcript
        and "Cumulative input tokens: 1155" in transcript
        and "Cumulative output tokens: 193" in transcript
    )
    record(
        "part4_conversation",
        transcript_valid,
        "Five-turn statistics found"
        if transcript_valid
        else "Expected five-turn statistics were not found"
    )
else:
    record(
        "part4_conversation",
        False,
        "Part 4 transcript was not found"
    )

overall = (
    "PASS"
    if all(check["status"] == "PASS" for check in checks)
    else "FAIL"
)

verification = {
    "homework": "hw01",
    "sid4": "2562",
    "verify_seed": VERIFY_SEED,
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "overall_status": overall,
    "checks": checks
}

OUTPUT.write_text(
    json.dumps(verification, indent=2),
    encoding="utf-8"
)

print(json.dumps(verification, indent=2))

if overall != "PASS":
    sys.exit(1)