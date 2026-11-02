"""HW8 configuration, JSON event logs, and Kafka factories (no mock transport)."""

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

SID4 = 2562
SEED = 2562
VERIFY_SEED = 262562
PREFIX = "s2562"
BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "127.0.0.1:9092")
REQUESTS = f"{PREFIX}_entity_requests"
RESPONSES = f"{PREFIX}_entity_responses"
INBOX, TASKS, DRAFTS, FINAL = (f"{PREFIX}_{name}" for name in ("inbox", "tasks", "drafts", "final"))
DEAD_LETTER = f"{PREFIX}_dead_letter"
TOPICS = {REQUESTS: 1, RESPONSES: 1, INBOX: 1, TASKS: 2, DRAFTS: 1, FINAL: 1, DEAD_LETTER: 1}
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "reports" / "hw08" / "raw"


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def emit(component, event, **fields):
    record = {"timestamp": utcnow(), "name": "Priyank Mehta", "component": component, "event": event, **fields}
    line = json.dumps(record, ensure_ascii=True, default=str)
    print(line, flush=True)
    path = Path(os.getenv("HW08_EVENT_DIR", str(RAW))) / f"events_{component}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(line + "\n")
    return record


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def producer(**kwargs):
    from aiokafka import AIOKafkaProducer

    return AIOKafkaProducer(
        bootstrap_servers=BOOTSTRAP,
        enable_idempotence=True,
        value_serializer=lambda value: json.dumps(value).encode(),
        **kwargs,
    )


def consumer(topic, group, **kwargs):
    from aiokafka import AIOKafkaConsumer

    options = {"auto_offset_reset": "earliest", **kwargs}
    return AIOKafkaConsumer(topic, bootstrap_servers=BOOTSTRAP, group_id=group, enable_auto_commit=False, **options)


def decode(raw):
    result = json.loads(raw)
    if not isinstance(result, dict):
        raise ValueError("Message must be a JSON object")
    return result
