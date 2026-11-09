"""Objective HW9 verifier. Offline mode explicitly does not certify external services."""

import argparse
import hashlib
import json
import subprocess
import sys

import yaml

from backend.hw09_common import DATA, MODEL, RAW, REPORT, ROOT, SEED, VERIFY_SEED, now


def verify(offline=False):
    checks = []

    def check(name, passed, **extra):
        checks.append({"name": name, "passed": bool(passed), **extra})

    tests = subprocess.run([sys.executable, "-m", "code.hw09_tests"], cwd=ROOT, capture_output=True, text=True)
    check("offline behavioral suite", tests.returncode == 0, output=tests.stdout + tests.stderr)
    cases = yaml.safe_load((ROOT / "cache_cases.yaml").read_text())["cases"]
    check(
        "40 labeled cases with ten per category",
        len(cases) == 40
        and all(
            sum(row["category"] == category for row in cases) == 10
            for category in ["exact", "paraphrase", "similar_different", "unrelated"]
        ),
    )
    check(
        "question-only input splits",
        all(
            all(set(row) == {"id", "question"} for row in json.loads((DATA / f"{split}_data.json").read_text()))
            for split in ["training", "validation", "test"]
        ),
    )
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if not offline:
        import httpx
        import redis

        from backend.hw09_common import REDIS_URL

        try:
            client = redis.Redis.from_url(REDIS_URL, socket_timeout=4)
            check("live Redis ping and vector index", client.ping() and bool(client.ft("s2562:index:live").info()))
            client.close()
        except Exception as error:
            check("live Redis ping and vector index", False, error=type(error).__name__)
        try:
            with httpx.Client(timeout=180) as client:
                health = client.get("http://127.0.0.1:8762/api/hw09/health").json()
                models = client.get("http://127.0.0.1:11434/api/tags").json()["models"]
                check("HW9 API on 8762", health.get("enabled") is True and health.get("homework") == 9)
                if (RAW / "threshold_choice.json").exists():
                    selected_threshold = json.loads((RAW / "threshold_choice.json").read_text())["selected"][
                        "threshold"
                    ]
                    check("API uses the selected shipping threshold", health.get("threshold") == selected_threshold)
                check("local model available", any(row["name"] == MODEL for row in models))
                if health.get("enabled"):
                    from sqlalchemy import text

                    from backend.database import engine
                    from backend.hw07_auth import create_access_token

                    with engine.connect() as connection:
                        user = (
                            connection.execute(text("SELECT id,role FROM users ORDER BY id LIMIT 1")).mappings().one()
                        )
                    token = create_access_token(str(user["id"]), user["role"] or "reader")
                    headers = {"Authorization": f"Bearer {token}"}
                    body = {"question": "What is the current severity of the Route 3 incident?"}
                    first = client.post("http://127.0.0.1:8762/api/hw09/qa", json=body, headers=headers)
                    second = client.post("http://127.0.0.1:8762/api/hw09/qa", json=body, headers=headers)
                    check(
                        "authenticated endpoint and repeated-query hit",
                        first.status_code == 200
                        and second.status_code == 200
                        and second.json().get("is_cached") is True,
                        first_response=first.json(),
                        second_response=second.json(),
                    )
        except Exception as error:
            check("live API and model connectivity", False, error=type(error).__name__)
        from code.hw09_experiments import committed_cases

        try:
            check(
                "labels committed before sweep",
                json.loads((RAW / "sweep_provenance.json").read_text())["sha256"] == committed_cases()["sha256"],
            )
        except (OSError, ValueError, RuntimeError) as error:
            check("labels committed before sweep", False, error=str(error))
        requirements = [
            "counter.json",
            "cache_queries.json",
            "cache_performance.json",
            "threshold_summary.json",
            "threshold_records.json",
            "false_hit.json",
            "threshold_choice.json",
            "stale_invalidation.json",
            "variant_runs.json",
            "variant_summary.json",
            "revision_sequences.json",
            "lesson_reuse.json",
            "lesson_validation.json",
        ]
        for name in requirements:
            check(f"evidence {name}", (RAW / name).exists())
        if all((RAW / name).exists() for name in requirements):

            def load(name):
                return json.loads((RAW / name).read_text())

            counter = load("counter.json")["records"]
            check(
                "25 real counter accesses",
                len(counter) == 25 and all(row["count"] == counter[0]["count"] + i for i, row in enumerate(counter)),
            )
            check("at least ten ingress queries", len(load("cache_queries.json")) >= 10)
            rows = load("threshold_records.json")
            check(
                "200 threshold calls, 40 per threshold",
                len(rows) == 200
                and all(sum(row["threshold"] == t for row in rows) == 40 for t in [0.75, 0.8, 0.85, 0.9, 0.95]),
            )
            summaries = load("threshold_summary.json")
            consistent = len(summaries) == 5
            for summary in summaries:
                group = [row for row in rows if row["threshold"] == summary["threshold"]]
                hits = sum(row["is_cached"] for row in group)
                false_hits = sum(row["is_cached"] and not row["should_hit"] for row in group)
                consistent = consistent and len(group) == 40 and summary["hits"] == hits
                consistent = consistent and summary["false_hits"] == false_hits
                consistent = consistent and summary["total_cost"] == round((40 - hits) * 0.002 + false_hits * 0.10, 4)
                consistent = (
                    consistent and abs(summary["mean_latency_ms"] - sum(row["latency_ms"] for row in group) / 40) < 1e-6
                )
            check("threshold metrics and costs reproduce from raw calls", consistent)
            check(
                "cache hits bypass the pipeline",
                all(row["correlation_id"] is None if row["is_cached"] else bool(row["correlation_id"]) for row in rows),
            )
            example = load("false_hit.json")
            check(
                "full false-hit evidence exists",
                example["is_cached"]
                and not example["should_hit"]
                and bool(example["cached_query"])
                and bool(example["answer"])
                and bool(example["correct_answer"]),
            )
            stale = load("stale_invalidation.json")
            check(
                "real stale hit then invalidation miss",
                stale["stale_hit"]["is_cached"]
                and not stale["after_invalidation"]["is_cached"]
                and stale["stale_hit"]["cached_version"] != stale["stale_hit"]["version"],
            )
            check(
                "stale answer preserved then changed after invalidation",
                stale["stale_hit"]["answer"] == stale["before"]["answer"]
                and stale["after_invalidation"]["answer"] != stale["before"]["answer"]
                and stale["fresh_hit"]["is_cached"]
                and stale["fresh_hit"]["answer"] == stale["after_invalidation"]["answer"],
            )
            variants = load("variant_runs.json")
            check(
                "four independent final variants, max two attempts",
                len(variants) == 4
                and all(1 <= run["attempt_count"] <= 2 for variant in variants for run in variant["runs"]),
            )
            sequences = load("revision_sequences.json")
            check(
                "failed then repaired sequence",
                any(
                    run["attempts"][0]["evaluation"]["result"] == "REVISE" and run["final_result"] == "PASS"
                    for run in sequences
                ),
            )
            check(
                "later question reloads a lesson",
                any(any(attempt["loaded_lessons"] for attempt in run["attempts"]) for run in load("lesson_reuse.json")),
            )
            held_out = (DATA / "test_data.json").read_bytes()
            selection = load("selection_provenance.json")
            check(
                "held-out inputs unchanged after lesson selection",
                hashlib.sha256(held_out).hexdigest() == selection["test_sha256"],
            )
            expected_questions = [item["question"] for item in json.loads(held_out)]
            check(
                "all variants use the identical held-out questions",
                all([run["question"] for run in variant["runs"]] == expected_questions for variant in variants),
            )
            validation = load("lesson_validation.json")
            check(
                "retained lesson passes the no-regression gate",
                not validation["keep"] or all(not row["regression"] for row in validation["comparisons"]),
            )
    source_paths = sorted(
        set(
            list((ROOT / "backend").glob("*hw09*.py"))
            + list((ROOT / "code").glob("*hw09*.py"))
            + [
                ROOT / name
                for name in [
                    "backend/main.py",
                    "backend/models.py",
                    "backend/crud.py",
                    "backend/routes_hw07.py",
                    "backend/hw08_agents.py",
                    "docker-compose.hw08.yml",
                    "docker-compose.hw09.yml",
                    "requirements.txt",
                    "verify_hw09.py",
                    "cache_cases.yaml",
                ]
            ]
        )
    )
    result = {
        "homework": "9",
        "sid4": "2562",
        "commit_hash": revision,
        "working_tree_dirty": bool(
            subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()
        ),
        "model": MODEL,
        "seed": SEED,
        "verify_seed": VERIFY_SEED,
        "timestamp": now(),
        "configuration": {
            "port_base": 8762,
            "prefix": "s2562",
            "domain_id": 2,
            "embedding": "sentence-transformers/all-MiniLM-L6-v2",
        },
        "mode": "offline" if offline else "live-evidence",
        "checks": checks,
        "overall_pass": all(item["passed"] for item in checks),
        "source_sha256": hashlib.sha256(
            b"".join(path.relative_to(ROOT).as_posix().encode() + path.read_bytes() for path in source_paths)
        ).hexdigest(),
    }
    REPORT.mkdir(parents=True, exist_ok=True)
    (REPORT / "verification.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("Priyank Mehta - HW9 verification")
    print(json.dumps(result, indent=2))
    return result["overall_pass"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true")
    raise SystemExit(0 if verify(parser.parse_args().offline) else 1)
