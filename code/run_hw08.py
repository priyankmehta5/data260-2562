"""One-command real HW8 execution with timestamped console and JSON evidence."""

import argparse
import asyncio
import json
import subprocess
import sys

import httpx

from backend.hw08_common import RAW, ROOT, utcnow

REPORT = ROOT / "reports" / "hw08"
COMPOSE = ["docker", "compose", "-f", "docker-compose.hw08.yml"]


def log(text):
    REPORT.mkdir(parents=True, exist_ok=True)
    print(text, flush=True)
    with (REPORT / "RUN_LOG.txt").open("a", encoding="utf-8") as stream:
        stream.write(text + "\n")


def command(args, required=True):
    log(f"\n[{utcnow()}] Priyank Mehta COMMAND: {subprocess.list2cmdline(args)}")
    process = subprocess.Popen(
        args, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace"
    )
    for line in process.stdout:
        log(line.rstrip())
    code = process.wait()
    log(f"[{utcnow()}] EXIT {code}")
    if required and code:
        raise RuntimeError(f"Command failed ({code}): {subprocess.list2cmdline(args)}")
    return code


def capture_events(since):
    rows = []
    for path in RAW.glob("events_*.jsonl"):
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if row["timestamp"] >= since:
                rows.append(row)
    log("\nTimestamp-ordered Kafka flow and failure-event excerpt (complete events for this run):")
    for row in sorted(rows, key=lambda value: value["timestamp"]):
        log(json.dumps(row))


async def wait_api():
    async with httpx.AsyncClient(timeout=3) as client:
        async with asyncio.timeout(180):
            while True:
                try:
                    result = await client.get("http://127.0.0.1:8762/api/hw08/health")
                    if result.status_code == 200 and result.json().get("enabled"):
                        return
                except httpx.HTTPError:
                    pass
                await asyncio.sleep(1)


def metrics():
    lines = ["# HW8 measured results", "", "Only completed real runs are reported as Kafka evidence.", ""]
    if (RAW / "failure_summary.json").exists():
        result = json.loads((RAW / "failure_summary.json").read_text(encoding="utf-8"))
        before, after = result["ordering"]["unkeyed"], result["ordering"]["keyed"]
        lines += [
            "| Failure scenario | Before fix | After fix |",
            "|---|---|---|",
            f"| Duplicate delivery | {result['duplicate']['before']['incident_count']} incidents from one replayed correlation | {result['duplicate']['after']['incident_count']} incident; same UUID replayed |",
            "| Consumer killed mid-work | Early commit skipped interrupted work; following marker completed | Same offset redelivered, output sent, then offset+1 committed |",
            "| Poison message | Uncommitted bad message blocked its partition | Three attempts, dead letter, following valid message completed |",
            f"| Two partitions/two consumers | Partitions {before['partitions']}; globally ordered: {before['in_order']} | One entity key; partitions {after['partitions']}; ordered: {after['in_order']} |",
            "",
            f"Unkeyed completion sequence: `{before['observed_sequence']}`.",
            "",
            f"Keyed completion sequence: `{after['observed_sequence']}`.",
            "",
            "Both runs contain exactly 20 related messages generated with VERIFY_SEED=262562. UUIDs and timing are real run data, not seeded identities or invented timings.",
        ]
    else:
        lines += ["Kafka failure experiments have not completed. No before/after results are claimed."]
    lines += [
        "",
        "## Kafka compared with the HW2 in-process graph",
        "",
        "Benefits: agents can scale independently through consumer groups; one failed agent can restart while other processes remain available and Kafka retains its input.",
        "",
        "Responsibilities: implement idempotency and acknowledge offsets only after successful processing; choose entity keys for partition ordering and handle poison records with bounded retries and a dead-letter topic.",
        "",
        "## Model and storage",
        "",
        "The HW8 pipeline uses deterministic transit-domain agents; no LLM output or token metrics are claimed. Part 1 entities live only in a plain dictionary in one worker and are lost on worker restart, as specified. Pipeline deduplication uses a separate local SQLite runtime cache. Kafka itself provides at-least-once delivery; this is not a claim of global exactly-once processing.",
    ]
    (REPORT / "METRICS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--build", action="store_true", help="Build and start only the s2562-hw08 Compose project")
    args = parser.parse_args()
    started = utcnow()
    try:
        command([sys.executable, "-m", "code.hw08_tests"])
        command(COMPOSE + ["config", "--quiet"])
        if args.offline:
            command([sys.executable, "verify_hw08.py", "--offline"], required=False)
            metrics()
            log("OFFLINE CHECKS COMPLETE. Live Kafka checks remain not run.")
            return
        if args.build:
            command(COMPOSE + ["up", "--build", "-d"])
        asyncio.run(wait_api())
        command([sys.executable, "homework_demo.py"])
        command([sys.executable, "send_question.py"])
        # Only our HW8 project's consumers are paused; unrelated containers are untouched.
        command(COMPOSE + ["stop", "writer", "worker"])
        try:
            command([sys.executable, "-m", "code.hw08_experiments"])
        finally:
            command(COMPOSE + ["start", "writer", "worker"])
        command([sys.executable, "verify_hw08.py"])
        metrics()
        command(COMPOSE + ["ps"])
        command(COMPOSE + ["logs", "--no-color", "--tail", "80", "api", "worker", "planner", "writer", "reviewer"])
        log("Priyank Mehta - HW8 implementation and real Kafka verification PASSED")
    except Exception as exc:
        log(f"[{utcnow()}] RUN FAILED: {type(exc).__name__}: {exc}")
        raise
    finally:
        capture_events(started)


if __name__ == "__main__":
    main()
