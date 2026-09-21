import csv
import hashlib
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports" / "hw03"
RAW_DIR = REPORT_DIR / "raw"

OUTPUT_FILE = REPORT_DIR / "verification.json"
RESULTS_FILE = RAW_DIR / "retrieval_results.csv"
MANIFEST_FILE = REPORT_DIR / "CORPUS_MANIFEST.json"
QUESTIONS_FILE = REPORT_DIR / "questions.yaml"

HOMEWORK_NUMBER = 3
SID4 = 2562
PORT_BASE = 8762
SEED = 2562
VERIFY_SEED = 262562

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEVICE = "CPU"
TOP_K = 5

checks = []


def add_check(name, passed, details):
    checks.append(
        {
            "name": name,
            "passed": bool(passed),
            "details": details,
        }
    )


def get_commit_hash():
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except Exception as error:
        return f"Unavailable: {type(error).__name__}: {error}"


def check_http_route(route):
    url = f"http://127.0.0.1:{PORT_BASE}{route}"

    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            status = response.status
            content = response.read()

        passed = status == 200 and len(content) > 0

        add_check(
            f"FastAPI route {route} responds",
            passed,
            (
                f"GET {url} returned HTTP {status}; "
                f"response_bytes={len(content)}"
            ),
        )
    except Exception as error:
        add_check(
            f"FastAPI route {route} responds",
            False,
            f"{type(error).__name__}: {error}",
        )


def check_retrieval_results():
    if not RESULTS_FILE.exists():
        add_check(
            "Retrieval results are complete",
            False,
            f"Missing file: {RESULTS_FILE}",
        )
        return

    try:
        with RESULTS_FILE.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as file:
            rows = list(csv.DictReader(file))

        required_columns = {
            "question_id",
            "technique",
            "rank",
            "source_file",
            "store_score",
            "cosine_similarity",
            "chunk_length",
            "retrieval_latency_ms",
            "expected_source",
            "expected_source_match",
            "preview",
        }

        actual_columns = set(rows[0].keys()) if rows else set()
        question_ids = {
            row["question_id"]
            for row in rows
        }
        techniques = {
            row["technique"]
            for row in rows
        }
        ranks = {
            int(row["rank"])
            for row in rows
        }

        expected_techniques = {
            "Token",
            "Semantic",
            "Sentence window",
        }

        passed = (
            len(rows) == 75
            and len(question_ids) == 5
            and techniques == expected_techniques
            and ranks == {1, 2, 3, 4, 5}
            and required_columns.issubset(actual_columns)
        )

        add_check(
            "Retrieval results are complete",
            passed,
            (
                f"rows={len(rows)}; "
                f"questions={len(question_ids)}; "
                f"techniques={sorted(techniques)}; "
                f"ranks={sorted(ranks)}"
            ),
        )
    except Exception as error:
        add_check(
            "Retrieval results are complete",
            False,
            f"{type(error).__name__}: {error}",
        )


def check_numeric_results():
    if not RESULTS_FILE.exists():
        add_check(
            "Retrieval metrics contain valid values",
            False,
            f"Missing file: {RESULTS_FILE}",
        )
        return

    try:
        with RESULTS_FILE.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as file:
            rows = list(csv.DictReader(file))

        valid = bool(rows)

        for row in rows:
            cosine = float(row["cosine_similarity"])
            chunk_length = int(row["chunk_length"])
            latency = float(row["retrieval_latency_ms"])

            if not (
                -1.0 <= cosine <= 1.0
                and chunk_length > 0
                and latency >= 0
            ):
                valid = False
                break

        add_check(
            "Retrieval metrics contain valid values",
            valid,
            (
                f"Validated cosine similarity, chunk length, "
                f"and latency for {len(rows)} rows"
            ),
        )
    except Exception as error:
        add_check(
            "Retrieval metrics contain valid values",
            False,
            f"{type(error).__name__}: {error}",
        )


def check_questions():
    if not QUESTIONS_FILE.exists():
        add_check(
            "Five precommitted questions exist",
            False,
            f"Missing file: {QUESTIONS_FILE}",
        )
        return

    try:
        content = QUESTIONS_FILE.read_text(encoding="utf-8")

        question_ids = re.findall(
            r"(?m)^\s*-\s*id:\s*[\"']?(q\d+)[\"']?\s*$",
            content,
        )
        expected_sources = re.findall(
            r"(?m)^\s*expected_source:\s*(.+?)\s*$",
            content,
        )

        passed = (
            sorted(question_ids)
            == ["q1", "q2", "q3", "q4", "q5"]
            and len(expected_sources) == 5
        )

        add_check(
            "Five precommitted questions exist",
            passed,
            (
                f"question_ids={sorted(question_ids)}; "
                f"expected_sources={len(expected_sources)}"
            ),
        )
    except Exception as error:
        add_check(
            "Five precommitted questions exist",
            False,
            f"{type(error).__name__}: {error}",
        )


def check_corpus_manifest():
    if not MANIFEST_FILE.exists():
        add_check(
            "Corpus manifest satisfies requirements",
            False,
            f"Missing file: {MANIFEST_FILE}",
        )
        return

    try:
        manifest = json.loads(
            MANIFEST_FILE.read_text(encoding="utf-8")
        )

        files = manifest.get("files", [])
        total_bytes = manifest.get("total_bytes", 0)

        valid_hashes = all(
            re.fullmatch(
                r"[0-9a-fA-F]{64}",
                str(item.get("sha256", "")),
            )
            for item in files
        )

        passed = (
            manifest.get("domain_id") == 2
            and len(files) >= 3
            and total_bytes >= 200_000
            and manifest.get("meets_size_requirement") is True
            and valid_hashes
        )

        add_check(
            "Corpus manifest satisfies requirements",
            passed,
            (
                f"domain_id={manifest.get('domain_id')}; "
                f"files={len(files)}; "
                f"total_bytes={total_bytes}; "
                f"valid_sha256={valid_hashes}"
            ),
        )
    except Exception as error:
        add_check(
            "Corpus manifest satisfies requirements",
            False,
            f"{type(error).__name__}: {error}",
        )


def check_saved_file_hashes():
    if not MANIFEST_FILE.exists():
        add_check(
            "Corpus files match manifest hashes",
            False,
            f"Missing file: {MANIFEST_FILE}",
        )
        return

    try:
        manifest = json.loads(
            MANIFEST_FILE.read_text(encoding="utf-8")
        )

        possible_directories = [
            ROOT / "data" / "hw03" / "corpus",
            REPORT_DIR / "corpus",
        ]

        mismatches = []
        checked = 0

        for item in manifest.get("files", []):
            filename = item["filename"]
            expected_hash = item["sha256"].lower()

            path = next(
                (
                    directory / filename
                    for directory in possible_directories
                    if (directory / filename).exists()
                ),
                None,
            )

            if path is None:
                mismatches.append(f"{filename}: missing")
                continue

            actual_hash = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()

            checked += 1

            if actual_hash != expected_hash:
                mismatches.append(f"{filename}: hash mismatch")

        passed = (
            checked == len(manifest.get("files", []))
            and not mismatches
        )

        add_check(
            "Corpus files match manifest hashes",
            passed,
            (
                f"checked={checked}; "
                f"problems={mismatches or 'none'}"
            ),
        )
    except Exception as error:
        add_check(
            "Corpus files match manifest hashes",
            False,
            f"{type(error).__name__}: {error}",
        )


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    check_http_route("/")
    check_http_route("/login")
    check_questions()
    check_corpus_manifest()
    check_saved_file_hashes()
    check_retrieval_results()
    check_numeric_results()

    verification = {
        "homework_number": HOMEWORK_NUMBER,
        "sid4": SID4,
        "commit_hash": get_commit_hash(),
        "model_configuration": {
            "embedding_model": EMBEDDING_MODEL,
            "device": DEVICE,
            "top_k": TOP_K,
            "port_base": PORT_BASE,
        },
        "seed": SEED,
        "verify_seed": VERIFY_SEED,
        "verified_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "checks": checks,
        "overall_passed": all(
            check["passed"]
            for check in checks
        ),
    }

    OUTPUT_FILE.write_text(
        json.dumps(
            verification,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            verification,
            indent=2,
            ensure_ascii=False,
        )
    )
    print(f"\nSaved: {OUTPUT_FILE}")

    return 0 if verification["overall_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())