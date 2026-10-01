import csv
import http.cookiejar
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports" / "hw04"
RAW_DIR = REPORT_DIR / "raw"
CORPUS_DIR = ROOT / "data" / "hw04" / "corpus"
OUTPUT_FILE = REPORT_DIR / "verification.json"

PORT = 8762
BASE_URL = f"http://127.0.0.1:{PORT}"
REFUSAL = (
    "I cannot answer this question from the provided documents"
)

checks = []
server_process = None


def add_check(name, passed, details):
    checks.append(
        {
            "name": name,
            "passed": bool(passed),
            "details": str(details)
        }
    )


def server_responds():
    try:
        with urllib.request.urlopen(
            f"{BASE_URL}/docs",
            timeout=3
        ) as response:
            return response.status == 200
    except Exception:
        return False


def start_server():
    global server_process

    if server_responds():
        return False

    server_process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "code.hw04.backend.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(PORT)
        ],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    for _ in range(30):
        if server_responds():
            return True
        time.sleep(1)

    return False


def stop_server():
    if server_process is not None:
        server_process.terminate()

        try:
            server_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server_process.kill()


def request_json(opener, method, path, body=None):
    data = None
    headers = {}

    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        headers=headers,
        method=method
    )

    with opener.open(request, timeout=30) as response:
        response_body = response.read().decode("utf-8")
        parsed = (
            json.loads(response_body)
            if response_body
            else None
        )
        return response.status, parsed


def count_records(payload):
    if isinstance(payload, list):
        return len(payload)

    if isinstance(payload, dict):
        for key in ["records", "incidents", "items", "data"]:
            value = payload.get(key)
            if isinstance(value, list):
                return len(value)

    return 0


def verify_api():
    started_here = start_server()
    add_check(
        "FastAPI responds on PORT_BASE",
        server_responds(),
        f"GET {BASE_URL}/docs returned successfully"
    )

    cookie_jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cookie_jar)
    )

    status, login = request_json(
        opener,
        "POST",
        "/api/login",
        {
            "email": "student@example.com",
            "password": "Transit2562!"
        }
    )

    add_check(
        "Login creates a server-side session",
        status == 200 and len(cookie_jar) > 0,
        (
            f"status={status}; "
            f"http_only_session_cookie_received="
            f"{len(cookie_jar) > 0}"
        )
    )

    naive_status, naive = request_json(
        opener,
        "GET",
        "/api/performance/incidents-naive?page_size=10"
    )

    fixed_status, fixed = request_json(
        opener,
        "GET",
        "/api/performance/incidents-optimized?page_size=10"
    )

    naive_queries = (
        naive.get("sql_queries")
        if isinstance(naive, dict)
        else None
    )
    fixed_queries = (
        fixed.get("sql_queries")
        if isinstance(fixed, dict)
        else None
    )

    add_check(
        "Naive list endpoint returns related data",
        (
            naive_status == 200
            and count_records(naive) == 10
            and naive_queries == 11
        ),
        (
            f"status={naive_status}; "
            f"records={count_records(naive)}; "
            f"sql_queries={naive_queries}"
        )
    )

    add_check(
        "Optimized list endpoint returns related data",
        (
            fixed_status == 200
            and count_records(fixed) == 10
            and fixed_queries == 1
        ),
        (
            f"status={fixed_status}; "
            f"records={count_records(fixed)}; "
            f"sql_queries={fixed_queries}"
        )
    )

    return started_here


def verify_database():
    from sqlalchemy import text

    backend_directory = (
        ROOT / "code" / "hw04" / "backend"
    )

    if str(backend_directory) not in sys.path:
        sys.path.insert(0, str(backend_directory))

    import database

    with database.engine.connect() as connection:
        incidents = connection.execute(
            text("SELECT COUNT(*) FROM incidents")
        ).scalar_one()

        notes = connection.execute(
            text("SELECT COUNT(*) FROM incident_notes")
        ).scalar_one()

    add_check(
        "Required database session variable exists",
        hasattr(database, "db_session_basede26"),
        "Checked code.hw04.backend.database"
    )

    add_check(
        "MySQL seed data exists",
        incidents >= 5000 and notes == 200,
        f"incidents={incidents}; incident_notes={notes}"
    )


def verify_n_plus_one_files():
    path = RAW_DIR / "n_plus_one_requests.csv"

    with path.open(encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    groups = {}

    for row in rows:
        key = (row["version"], int(row["page_size"]))
        groups[key] = groups.get(key, 0) + 1

    expected = {
        ("naive", 10): 30,
        ("naive", 50): 30,
        ("naive", 200): 30,
        ("optimized", 10): 30,
        ("optimized", 50): 30,
        ("optimized", 200): 30
    }

    add_check(
        "All 180 N+1 requests are saved",
        len(rows) == 180 and groups == expected,
        f"rows={len(rows)}; groups={groups}"
    )


def verify_rag_files():
    corpus_files = [
        path
        for path in CORPUS_DIR.iterdir()
        if path.is_file()
    ]

    add_check(
        "RAG corpus contains at least five documents",
        len(corpus_files) >= 5,
        (
            f"files={len(corpus_files)}; "
            f"names={[path.name for path in corpus_files]}"
        )
    )

    retrievals = json.loads(
        (RAW_DIR / "retrieved_chunks.json").read_text(
            encoding="utf-8"
        )
    )

    comparisons = json.loads(
        (
            RAW_DIR / "configuration_comparison.json"
        ).read_text(encoding="utf-8")
    )

    sweep = json.loads(
        (RAW_DIR / "k_sweep.json").read_text(
            encoding="utf-8"
        )
    )

    evaluation = json.loads(
        (RAW_DIR / "rag_evaluation.json").read_text(
            encoding="utf-8"
        )
    )

    add_check(
        "Six questions have printed top-k retrievals",
        (
            len(retrievals) == 6
            and all(
                len(item["results"]) == 3
                for item in retrievals
            )
        ),
        (
            f"questions={len(retrievals)}; "
            f"top_k_counts="
            f"{[len(item['results']) for item in retrievals]}"
        )
    )

    configurations = {
        item["configuration"]
        for item in comparisons
    }

    add_check(
        "Three-configuration comparison is complete",
        (
            len(comparisons) == 18
            and configurations == {"A", "B", "C"}
        ),
        (
            f"rows={len(comparisons)}; "
            f"configurations={sorted(configurations)}"
        )
    )

    sweep_values = sorted(
        item["k"]
        for item in sweep
    )

    add_check(
        "Top-k sweep contains k=1, 3, and 5",
        sweep_values == [1, 3, 5],
        f"k_values={sweep_values}"
    )

    refusal_results = {
        item["question_id"]: item["answer"].strip()
        for item in comparisons
        if (
            item["configuration"] == "C"
            and item["question_id"] in {"Q5", "Q6"}
        )
    }

    add_check(
        "Context RAG refuses Q5 and Q6",
        (
            refusal_results.get("Q5") == REFUSAL
            and refusal_results.get("Q6") == REFUSAL
        ),
        f"answers={refusal_results}"
    )

    add_check(
        "RAG evaluation contains all 18 rows",
        len(evaluation) == 18,
        f"evaluation_rows={len(evaluation)}"
    )


def commit_hash():
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True
    ).strip()


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    started_here = False

    try:
        started_here = verify_api()
        verify_database()
        verify_n_plus_one_files()
        verify_rag_files()
    except Exception as error:
        add_check(
            "Verification script completed",
            False,
            f"{type(error).__name__}: {error}"
        )
    finally:
        if started_here:
            stop_server()

    result = {
        "homework_number": 4,
        "sid4": 2562,
        "commit_hash": commit_hash(),
        "model_configuration": {
            "llm": "qwen3:1.7b",
            "embedding_model": (
                "sentence-transformers/all-MiniLM-L6-v2"
            ),
            "device": "CPU",
            "chunk_size": 500,
            "chunk_overlap": 50,
            "default_top_k": 3,
            "port_base": PORT,
            "database": "s2562_rel"
        },
        "seed": 2562,
        "verify_seed": 262562,
        "verified_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "checks": checks,
        "overall_passed": (
            bool(checks)
            and all(check["passed"] for check in checks)
        )
    }

    OUTPUT_FILE.write_text(
        json.dumps(result, indent=2),
        encoding="utf-8"
    )

    print(json.dumps(result, indent=2))

    raise SystemExit(
        0 if result["overall_passed"] else 1
    )


if __name__ == "__main__":
    main()