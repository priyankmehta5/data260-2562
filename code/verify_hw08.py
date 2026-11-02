"""HW8 objective smoke checks. Offline checks never certify Kafka integration."""

import argparse
import asyncio
import hashlib
import json
import platform
import subprocess
import sys
from uuid import uuid4

import httpx
from aiokafka.admin import AIOKafkaAdminClient

from backend.hw08_common import BOOTSTRAP, PREFIX, RAW, ROOT, SEED, SID4, TOPICS, VERIFY_SEED, utcnow


def load(name):
    return json.loads((RAW / name).read_text(encoding="utf-8"))


async def verify(offline=False, require_tag=False):
    checks = []

    def check(name, passed, **evidence):
        checks.append({"name": name, "passed": bool(passed), **evidence})

    tests = subprocess.run([sys.executable, "-m", "code.hw08_tests"], cwd=ROOT, capture_output=True, text=True)
    check("offline behavioral tests", tests.returncode == 0, output=tests.stdout + tests.stderr)
    try:
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except subprocess.CalledProcessError:
        revision = None
    tag_result = subprocess.run(["git", "rev-parse", "hw8^{commit}"], cwd=ROOT, capture_output=True, text=True)
    tag_commit = tag_result.stdout.strip() if tag_result.returncode == 0 else None
    if require_tag:
        check("hw8 tag matches current commit", tag_commit == revision and revision is not None)
    if not offline:
        try:
            admin = AIOKafkaAdminClient(bootstrap_servers=BOOTSTRAP, request_timeout_ms=10000)
            await admin.start()
            try:
                metadata = await admin.describe_topics(list(TOPICS))
                actual = {item["topic"]: len(item["partitions"]) for item in metadata if item["error_code"] == 0}
                check("all seven prefixed topics and partition counts", actual == TOPICS, observed=actual)
            finally:
                await admin.close()
        except Exception as exc:
            check("Kafka connectivity and topics", False, error=str(exc))
        try:
            async with httpx.AsyncClient(timeout=25) as client:
                health = (await client.get("http://127.0.0.1:8762/api/hw08/health")).json()
                check("FastAPI on PORT_BASE 8762", health.get("enabled") is True and health.get("homework") == "8")
                from homework_demo import demonstrate

                demo = await demonstrate()
                check(
                    "CREATE_INCIDENT then GET_INCIDENT through Kafka",
                    demo["correlation_preserved"] and demo["get_response"]["success"],
                )
                for operation, data, label in [
                    ("GET_INCIDENT", {"incident_id": str(uuid4())}, "unknown UUID"),
                    ("CREATE_INCIDENT", {}, "missing required incident fields"),
                    ("UNKNOWN", {}, "unknown operation"),
                ]:
                    from backend.hw08_rpc import make_request

                    request = make_request(operation, data)
                    response = (await client.post("http://127.0.0.1:8762/api/hw08/incidents", json=request)).json()
                    check(
                        label,
                        response.get("success") is False
                        and response.get("correlation_id") == request["correlation_id"],
                        response=response,
                    )
            from send_question import send_question

            final = await send_question()
            check("three-process pipeline final JSON", final.get("status") == "approved" and bool(final.get("answer")))
        except Exception as exc:
            check("live request/response and pipeline smoke", False, error=str(exc))
        try:
            duplicate = load("duplicate_delivery.json")
            check(
                "replay before/after side effects",
                duplicate["before"]["incident_count"] == 2
                and duplicate["after"]["incident_count"] == 1
                and duplicate["after"]["same_uuid"],
            )
            death = load("consumer_death.json")
            check(
                "killed Writer restart and offsets",
                death["before"]["lost_before_fix"] and death["after"]["redelivered_and_completed"],
            )
            poison = load("poison_message.json")
            check(
                "poison retries, dead letter, later-message progress",
                len(poison["after"]["retry_events"]) == 3
                and poison["after"]["dead_letter"]["message"]["attempts"] == 3
                and poison["after"]["later_message"]["event"] == "sent",
            )
            for mode in ("unkeyed", "keyed"):
                ordering = load(f"ordering_{mode}.json")
                good = len(ordering["records"]) == 20 and ordering["verify_seed"] == VERIFY_SEED
                good = good and len({x["correlation_id"] for x in ordering["records"]}) == 20
                good = good and len(ordering["two_writer_instances"]) == 2
                if mode == "keyed":
                    good = good and ordering["in_order"] and len(ordering["partitions"]) == 1
                else:
                    good = good and len(ordering["partitions"]) == 2
                check(f"20-message {mode} ordering", good, observed_sequence=ordering["observed_sequence"])
        except (OSError, ValueError, KeyError) as exc:
            check("complete real failure evidence", False, error=str(exc))
    else:
        check(
            "Kafka integration and failure experiments",
            False,
            status="not_run",
            reason="Offline mode does not test Kafka",
        )
    paths = [
        *ROOT.glob("backend/*hw08*.py"),
        ROOT / "homework_demo.py",
        ROOT / "planner.py",
        ROOT / "writer.py",
        ROOT / "reviewer.py",
        ROOT / "send_question.py",
        ROOT / "code" / "hw08_experiments.py",
    ]
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(path.relative_to(ROOT).as_posix().encode() + path.read_bytes())
    result = {
        "homework": "8",
        "sid4": str(SID4),
        "commit_hash": revision,
        "tag_commit": tag_commit,
        "model": "qwen3:1.7b (personal configuration; HW8 agents use deterministic domain rules)",
        "configuration": {
            "port_base": 8762,
            "prefix": PREFIX,
            "domain_id": 2,
            "transport": "Kafka",
            "agent_mode": "deterministic",
            "bootstrap": BOOTSTRAP,
        },
        "seed": SEED,
        "verify_seed": VERIFY_SEED,
        "platform": platform.platform(),
        "timestamp": utcnow(),
        "source_digest_sha256": digest.hexdigest(),
        "checks": checks,
        "overall_pass": all(row["passed"] for row in checks),
        "mode": "offline" if offline else "live",
    }
    folder = ROOT / "reports" / "hw08"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "verification.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("Priyank Mehta - HW8 verification")
    print(json.dumps(result, indent=2))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--require-tag", action="store_true")
    args = parser.parse_args()
    result = asyncio.run(verify(args.offline, args.require_tag))
    raise SystemExit(0 if result["overall_pass"] else 1)


if __name__ == "__main__":
    main()
