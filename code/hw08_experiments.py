"""Real Kafka failure experiments. No synthetic success records or fixed output tables.

Only processes started by this runner are killed. The normal HW8 worker/Writer are
temporarily stopped by the caller to avoid competing with the controlled experiments.
"""

import asyncio
import csv
import json
import os
import random
import subprocess
import sys
from uuid import uuid4

from aiokafka import AIOKafkaConsumer, TopicPartition

from backend.hw08_common import (
    BOOTSTRAP,
    DEAD_LETTER,
    DRAFTS,
    RAW,
    ROOT,
    TASKS,
    VERIFY_SEED,
    consumer,
    decode,
    emit,
    producer,
)
from backend.hw08_rpc import KafkaRPC, make_request


def save(name, data):
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / name).write_text(json.dumps(data, indent=2), encoding="utf-8")


def events(instance):
    path = RAW / f"events_{instance}.jsonl"
    if not path.exists():
        return []
    result = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            result.append(json.loads(line))
        except json.JSONDecodeError:
            continue  # A concurrently appended last line may still be incomplete.
    return result


async def wait_event(instance, predicate, timeout=45):
    async with asyncio.timeout(timeout):
        while True:
            for event in events(instance):
                if predicate(event):
                    return event
            await asyncio.sleep(0.1)


class Child:
    def __init__(self, module, group, instance, *flags):
        self.instance = instance
        folder = RAW / "processes"
        folder.mkdir(parents=True, exist_ok=True)
        self.stream = (folder / f"{instance}.txt").open("a", encoding="utf-8")
        command = [
            sys.executable,
            "-u",
            "-m",
            module,
            "--group",
            group,
            "--instance",
            instance,
            "--start-latest",
            *(["--fault-injection"] if module == "writer" else []),
            *flags,
        ]
        self.process = subprocess.Popen(
            command,
            cwd=ROOT,
            stdout=self.stream,
            stderr=subprocess.STDOUT,
            env={**os.environ, "PYTHONUNBUFFERED": "1", "HW08_DEDUP_DB": str(RAW / "state" / f"{group}.sqlite3")},
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        emit("experiments", "process_started", pid=self.process.pid, instance=instance, command=command)

    async def ready(self):
        return await wait_event(self.instance, lambda event: event["event"] == "ready")

    def kill(self):
        if self.process.poll() is None:
            self.process.kill()
            self.process.wait(timeout=15)
            emit("experiments", "process_killed", pid=self.process.pid, instance=self.instance)
        self.stream.close()


async def committed(group, partition):
    reader = AIOKafkaConsumer(bootstrap_servers=BOOTSTRAP, group_id=group, enable_auto_commit=False)
    tp = TopicPartition(TASKS, partition)
    reader.assign([tp])
    await reader.start()
    try:
        return await reader.committed(tp)
    finally:
        await reader.stop()


async def collect(reader, ids, timeout=60):
    rows = []
    async with asyncio.timeout(timeout):
        while len(rows) < len(ids):
            record = await reader.getone()
            message = decode(record.value)
            if message.get("correlation_id") in ids:
                rows.append(
                    {
                        "message": message,
                        "broker_partition": record.partition,
                        "broker_offset": record.offset,
                        "observed_order": len(rows),
                    }
                )
    return rows


async def duplicate_test():
    summary = {}
    for enabled in (False, True):
        mode = "after" if enabled else "before"
        token = uuid4().hex[:10]
        instance = f"duplicate-{mode}-{token}"
        flags = [] if enabled else ["--disable-idempotency"]
        child = Child("backend.hw08_worker", f"s2562_duplicate_{token}", instance, *flags)
        rpc = KafkaRPC(f"duplicate-client-{token}")
        try:
            await child.ready()
            await rpc.start()
            request = make_request(
                "CREATE_INCIDENT",
                {
                    "title": "Duplicate replay test",
                    "description": "Same correlation sent twice",
                    "incident_code": "DUP-" + token.upper(),
                    "severity": 2,
                    "agency_id": 1,
                },
            )
            first = await rpc.request(request)
            replay = await rpc.request(request)
            assert first["success"] and replay["success"], (first, replay)
            observed = [event for event in events(instance) if event["event"] == "request_processed"]
            count = observed[-1]["incident_count"]
            assert count == (1 if enabled else 2)
            summary[mode] = {
                "idempotency_enabled": enabled,
                "first": first,
                "replay": replay,
                "incident_count": count,
                "same_uuid": first["incident_id"] == replay["incident_id"],
                "events": observed,
            }
        finally:
            if hasattr(rpc, "task"):
                await rpc.stop()
            child.kill()
    save("duplicate_delivery.json", summary)
    return summary


async def death_test(sender):
    summary = {}
    for unsafe in (True, False):
        mode = "before" if unsafe else "after"
        token = uuid4().hex[:10]
        group, instance = f"s2562_death_{token}", f"death-{mode}-{token}"
        flags = ["--unsafe-commit"] if unsafe else []
        child = Child("writer", group, instance, *flags)
        cid = str(uuid4())
        message = {
            "correlation_id": cid,
            "question": "Consumer-death test",
            "plan": ["review"],
            "processing_delay_s": 0,
            "hold_until_killed": True,
        }
        try:
            await child.ready()
            sent = await sender.send_and_wait(TASKS, message, partition=0)
            await wait_event(
                instance, lambda event: event["event"] == "processing" and event.get("correlation_id") == cid
            )
            await wait_event(
                instance, lambda event: event["event"] == "waiting_for_kill" and event.get("correlation_id") == cid
            )
            at_kill = await committed(group, 0)
            child.kill()
            assert (at_kill > sent.offset) if unsafe else (at_kill <= sent.offset)
            emit(
                "experiments",
                "offset_at_death",
                group=group,
                mode=mode,
                source_offset=sent.offset,
                committed_next_offset=at_kill,
                correlation_id=cid,
            )
            restarted = Child("writer", group, instance + "-restart", *flags, "--resume-interrupted")
            child = restarted
            await child.ready()
            if unsafe:
                # Demonstrate progress past the lost record, rather than inferring loss from a short timeout.
                marker = {"correlation_id": str(uuid4()), "question": "Following marker", "plan": ["review"]}
                await sender.send_and_wait(TASKS, marker, partition=0)
                await wait_event(
                    child.instance,
                    lambda e: e["event"] == "sent" and e.get("correlation_id") == marker["correlation_id"],
                )
                redelivered = any(e.get("correlation_id") == cid for e in events(child.instance))
                assert not redelivered
                result = {"lost_before_fix": True, "following_marker_completed": True}
            else:
                completed_event = await wait_event(
                    child.instance, lambda e: e["event"] == "sent" and e.get("correlation_id") == cid
                )
                committed_event = await wait_event(
                    child.instance,
                    lambda e: e["event"] == "offset_committed_after_processing" and e.get("correlation_id") == cid,
                )
                assert committed_event["next_offset"] == sent.offset + 1
                result = {"redelivered_and_completed": True, "completed": completed_event, "commit": committed_event}
            summary[mode] = {
                "correlation_id": cid,
                "source_offset": sent.offset,
                "committed_next_offset_at_kill": at_kill,
                "group": group,
                "unsafe_early_commit": unsafe,
                **result,
            }
        finally:
            child.kill()
    save("consumer_death.json", summary)
    return summary


async def poison_test(sender):
    token = uuid4().hex[:10]
    group, instance = f"s2562_poison_{token}", f"poison-before-{token}"
    poison = {"correlation_id": str(uuid4()), "question": 27, "plan": ["invalid numeric question"]}
    good = {"correlation_id": str(uuid4()), "question": "Valid message after poison", "plan": ["review"]}
    child = Child("writer", group, instance, "--halt-on-poison")
    dead_reader = consumer(DEAD_LETTER, f"s2562_dead_observer_{token}")
    await dead_reader.start()
    try:
        await child.ready()
        metadata = await sender.send_and_wait(TASKS, poison, partition=0)
        await sender.send_and_wait(TASKS, good, partition=0)
        blocked = await wait_event(instance, lambda event: event["event"] == "poison_blocks_partition")
        initial_offset = await committed(group, 0)
        assert initial_offset <= metadata.offset
        child.kill()
        child = Child("writer", group, f"poison-after-{token}")
        await child.ready()
        success = await wait_event(
            child.instance, lambda e: e["event"] == "sent" and e.get("correlation_id") == good["correlation_id"]
        )
        retries = [
            e
            for e in events(child.instance)
            if e["event"] == "retry" and e.get("correlation_id") == poison["correlation_id"]
        ]
        assert len(retries) == 3
        dead = (await collect(dead_reader, {poison["correlation_id"]}))[0]
        assert dead["message"]["attempts"] == 3
        result = {
            "before": {"blocked": blocked, "committed_next_offset": initial_offset},
            "after": {"retry_limit": 3, "retry_events": retries, "dead_letter": dead, "later_message": success},
        }
        save("poison_message.json", result)
        return result
    finally:
        child.kill()
        await dead_reader.stop()


async def ordering_test(sender):
    rng = random.Random(VERIFY_SEED)
    inputs = [
        {
            "sequence": index,
            "related_entity": "route-2",
            "sample": rng.randrange(10000),
            "processing_delay_s": round(rng.uniform(0.01, 0.12), 4),
        }
        for index in range(20)
    ]
    summary = {}
    for keyed in (False, True):
        mode = "keyed" if keyed else "unkeyed"
        token = uuid4().hex[:10]
        group = f"s2562_order_{token}"
        children = [Child("writer", group, f"order-{mode}-{token}-{i}") for i in range(2)]
        observer = consumer(DRAFTS, f"s2562_order_observer_{token}")
        await observer.start()
        try:
            await asyncio.gather(*(child.ready() for child in children))
            # Wait for the group to settle at TWO members, each assigned ONE of the two partitions.
            from aiokafka.admin import AIOKafkaAdminClient

            admin = AIOKafkaAdminClient(bootstrap_servers=BOOTSTRAP)
            await admin.start()
            try:
                async with asyncio.timeout(30):
                    while True:
                        descriptions = await admin.describe_consumer_groups([group])
                        description = descriptions[0].to_object()["groups"][0]
                        if len(description["members"]) == 2 and description["state"] == "Stable":
                            break
                        await asyncio.sleep(0.2)
            finally:
                await admin.close()
            requests = []
            ids = set()
            for row in inputs:
                message = {
                    **row,
                    "correlation_id": str(uuid4()),
                    "question": "Related Route 2 incident update",
                    "plan": ["review"],
                }
                ids.add(message["correlation_id"])
                # Before: explicitly round-robin unkeyed records; after: Kafka hashes the entity key.
                meta = await sender.send_and_wait(
                    TASKS, message, key=b"route-2" if keyed else None, partition=None if keyed else row["sequence"] % 2
                )
                requests.append({**message, "source_partition": meta.partition, "source_offset": meta.offset})
            received = await collect(observer, ids)
            async with asyncio.timeout(10):
                while (
                    sum(
                        e["event"] == "sent" and e.get("correlation_id") in ids
                        for child in children
                        for e in events(child.instance)
                    )
                    < 20
                ):
                    await asyncio.sleep(0.05)
            event_map = {
                e["correlation_id"]: e for child in children for e in events(child.instance) if e["event"] == "sent"
            }
            records = [
                {
                    **row["message"],
                    "observed_order": row["observed_order"],
                    "source_partition": event_map[row["message"]["correlation_id"]]["source_partition"],
                    "writer": event_map[row["message"]["correlation_id"]]["component"],
                    "draft_offset": row["broker_offset"],
                }
                for row in received
            ]
            observed = [row["sequence"] for row in records]
            assert len(records) == 20 and len(set(observed)) == 20
            partitions = sorted({row["source_partition"] for row in records})
            if keyed:
                assert len(partitions) == 1 and observed == list(range(20))
            else:
                assert len(partitions) == 2
            result = {
                "verify_seed": VERIFY_SEED,
                "group": group,
                "two_writer_instances": [c.instance for c in children],
                "key": "route-2" if keyed else None,
                "input": requests,
                "records": records,
                "observed_sequence": observed,
                "partitions": partitions,
                "in_order": observed == list(range(20)),
            }
            save(f"ordering_{mode}.json", result)
            with (RAW / f"ordering_{mode}.csv").open("w", newline="", encoding="utf-8") as stream:
                fields = ["sequence", "observed_order", "source_partition", "writer", "draft_offset", "correlation_id"]
                writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(records)
            summary[mode] = result
        finally:
            for child in children:
                child.kill()
            await observer.stop()
    return summary


async def run_experiments():
    sender = producer()
    await sender.start()
    try:
        results = {
            "duplicate": await duplicate_test(),
            "consumer_death": await death_test(sender),
            "poison": await poison_test(sender),
            "ordering": await ordering_test(sender),
        }
        save("failure_summary.json", results)
        return results
    finally:
        await sender.stop()


if __name__ == "__main__":
    asyncio.run(run_experiments())
