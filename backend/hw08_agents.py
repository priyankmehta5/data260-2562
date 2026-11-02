"""Planner, Writer and Reviewer are separate OS processes; Kafka carries every exchange.

Deterministic domain agents keep the messaging experiments repeatable. No LLM or paid API
is required by HW8. SQLite stores only pipeline deduplication results, never Part 1 entities.
"""

import argparse
import asyncio
import json
import os
import sqlite3

from aiokafka import TopicPartition

from .hw08_common import DEAD_LETTER, DRAFTS, FINAL, INBOX, RAW, TASKS, consumer, decode, emit, fingerprint, producer

STAGES = {"planner": (INBOX, TASKS), "writer": (TASKS, DRAFTS), "reviewer": (DRAFTS, FINAL)}


def transform(stage, message):
    cid = message.get("correlation_id")
    if not isinstance(cid, str) or not cid.strip():
        raise ValueError("correlation_id is required")
    question = message.get("question")
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question must be nonempty text")
    result = dict(message)
    if stage == "planner":
        result["plan"] = [
            "Identify affected route and incident severity",
            "Explain a safe response",
            "State verification steps",
        ]
    elif stage == "writer":
        if not isinstance(message.get("plan"), list) or not message["plan"]:
            raise ValueError("Writer requires a nonempty plan")
        result["draft"] = (
            f"For the transit question '{question}', confirm the affected route, time, and severity. "
            "Notify transit operations and follow the agency safety-review procedure. "
            "Verify the incident record and any service advisory before reporting resolution."
        )
    else:
        if not isinstance(message.get("draft"), str) or not message["draft"].strip():
            raise ValueError("Reviewer requires a nonempty draft")
        result.update(status="approved", answer=message["draft"])
    result["stage"] = stage
    return result


class DedupStore:
    def __init__(self, path):
        path = os.fspath(path)
        self.db = sqlite3.connect(path, timeout=30)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS results (scope TEXT, cid TEXT, fingerprint TEXT, output TEXT, PRIMARY KEY(scope,cid))"
        )
        self.db.commit()

    def get(self, scope, message):
        row = self.db.execute(
            "SELECT fingerprint,output FROM results WHERE scope=? AND cid=?", (scope, message["correlation_id"])
        ).fetchone()
        if row:
            if row[0] != fingerprint(message):
                raise ValueError("correlation_id reused with different message")
            return json.loads(row[1])

    def save(self, scope, message, output):
        self.db.execute(
            "INSERT OR IGNORE INTO results VALUES (?,?,?,?)",
            (scope, message["correlation_id"], fingerprint(message), json.dumps(output)),
        )
        self.db.commit()


async def run_agent(
    stage,
    group=None,
    instance=None,
    unsafe_commit=False,
    start_latest=False,
    halt_on_poison=False,
    fault_injection=False,
    resume_interrupted=False,
):
    source, destination = STAGES[stage]
    group = group or f"s2562_{stage}"
    instance = instance or stage
    reader, sender = (
        consumer(
            source,
            group,
            session_timeout_ms=6000,
            heartbeat_interval_ms=1000,
            auto_offset_reset="latest" if start_latest else "earliest",
        ),
        producer(),
    )
    state_path = os.getenv("HW08_DEDUP_DB", str(RAW / "state" / "pipeline.sqlite3"))
    from pathlib import Path

    Path(state_path).parent.mkdir(parents=True, exist_ok=True)
    store = DedupStore(state_path)
    await sender.start()
    await reader.start()
    async with asyncio.timeout(30):
        while not reader.assignment():
            await asyncio.sleep(0.1)
        for tp in reader.assignment():
            position = await reader.position(tp)
            if await reader.committed(tp) is None:
                # Establish the experiment's starting position before its first input is sent.
                await reader.commit({tp: position})
    emit(
        instance,
        "ready",
        stage=stage,
        group=group,
        topic=source,
        partitions=sorted(tp.partition for tp in reader.assignment()),
    )
    try:
        async for record in reader:
            tp = TopicPartition(record.topic, record.partition)
            message = None
            emit(
                instance,
                "received",
                stage=stage,
                group=group,
                topic=source,
                partition=record.partition,
                offset=record.offset,
                raw=(record.value or b"").decode(errors="replace"),
            )
            if unsafe_commit:
                await reader.commit({tp: record.offset + 1})
                emit(
                    instance,
                    "unsafe_commit_before_processing",
                    partition=record.partition,
                    next_offset=record.offset + 1,
                )
            for attempt in range(1, 4):
                try:
                    message = decode(record.value)
                    # Deliberate latency is experiment input, not a model/benchmark measurement.
                    delay = (
                        min(30.0, max(0.0, float(message.get("processing_delay_s", 0))))
                        if stage == "writer" and fault_injection
                        else 0
                    )
                    emit(
                        instance,
                        "processing",
                        correlation_id=message.get("correlation_id"),
                        attempt=attempt,
                        partition=record.partition,
                        offset=record.offset,
                        delay_s=delay,
                    )
                    await asyncio.sleep(delay)
                    if (
                        stage == "writer"
                        and fault_injection
                        and message.get("hold_until_killed")
                        and not resume_interrupted
                    ):
                        emit(
                            instance,
                            "waiting_for_kill",
                            correlation_id=message["correlation_id"],
                            partition=record.partition,
                            offset=record.offset,
                        )
                        await asyncio.Event().wait()
                    cached = store.get(group, message)
                    result = cached or transform(stage, message)
                    if cached is None:
                        store.save(group, message, result)
                    else:
                        emit(instance, "duplicate_suppressed", correlation_id=message["correlation_id"])
                    # Cached output may be re-published after a crash; downstream stages deduplicate it.
                    metadata = await sender.send_and_wait(
                        destination, result, key=str(message.get("related_entity", message["correlation_id"])).encode()
                    )
                    emit(
                        instance,
                        "sent",
                        stage=stage,
                        topic=destination,
                        correlation_id=message["correlation_id"],
                        source_partition=record.partition,
                        source_offset=record.offset,
                        output_offset=metadata.offset,
                        duplicate=cached is not None,
                        message=result,
                    )
                    break
                except (ValueError, TypeError, KeyError, UnicodeError) as exc:
                    emit(
                        instance,
                        "retry",
                        attempt=attempt,
                        error=str(exc),
                        correlation_id=(message or {}).get("correlation_id"),
                        partition=record.partition,
                        offset=record.offset,
                    )
                    if halt_on_poison:
                        # Explicit before-fix mode: leave the offset uncommitted and later work blocked.
                        emit(instance, "poison_blocks_partition", partition=record.partition, offset=record.offset)
                        await asyncio.Event().wait()
                    if attempt == 3:
                        dead = {
                            "correlation_id": (message or {}).get("correlation_id"),
                            "success": False,
                            "error": str(exc),
                            "attempts": attempt,
                            "source_topic": source,
                            "partition": record.partition,
                            "offset": record.offset,
                            "original": (record.value or b"").decode(errors="replace"),
                        }
                        await sender.send_and_wait(DEAD_LETTER, dead)
                        emit(instance, "dead_letter", message=dead, topic=DEAD_LETTER)
                    else:
                        await asyncio.sleep(0.1 * 2 ** (attempt - 1))
            if not unsafe_commit:
                await reader.commit({tp: record.offset + 1})
                emit(
                    instance,
                    "offset_committed_after_processing",
                    partition=record.partition,
                    next_offset=record.offset + 1,
                    correlation_id=(message or {}).get("correlation_id"),
                )
    finally:
        await reader.stop()
        await sender.stop()
        store.db.close()


def main(stage=None):
    parser = argparse.ArgumentParser()
    if stage is None:
        parser.add_argument("stage", choices=STAGES)
    parser.add_argument("--group")
    parser.add_argument("--instance")
    parser.add_argument("--unsafe-commit", action="store_true", help="Baseline failure experiment only")
    parser.add_argument("--start-latest", action="store_true", help="New isolated experiment group only")
    parser.add_argument("--halt-on-poison", action="store_true", help="Before-fix poison experiment only")
    parser.add_argument(
        "--fault-injection", action="store_true", help="Enable controlled experimental latency and holds"
    )
    parser.add_argument(
        "--resume-interrupted", action="store_true", help="Resume the controlled mid-processing crash case"
    )
    args = parser.parse_args()
    asyncio.run(
        run_agent(
            stage or args.stage,
            args.group,
            args.instance,
            args.unsafe_commit,
            args.start_latest,
            args.halt_on_poison,
            args.fault_injection,
            args.resume_interrupted,
        )
    )


if __name__ == "__main__":
    main()
