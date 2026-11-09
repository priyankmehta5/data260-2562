"""Shared HW9 configuration and timestamped evidence; no credentials in logs."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/hw09"
RAW = REPORT / "raw"
DATA = REPORT / "data"
PREFIX = "s2562"
SEED, VERIFY_SEED = 2562, 262562
MODEL = "qwen3:1.7b"
EMBEDDING = "sentence-transformers/all-MiniLM-L6-v2"
REDIS_URL = os.getenv("HW09_REDIS_URL", "redis://127.0.0.1:6379/0")


def now():
    return datetime.now(timezone.utc).isoformat()


def save(name, value):
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / name).write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def event(kind, **fields):
    row = {"timestamp": now(), "name": "Priyank Mehta", "event": kind, **fields}
    RAW.mkdir(parents=True, exist_ok=True)
    line = json.dumps(row, ensure_ascii=True, default=str)
    print(line, flush=True)
    with (RAW / "events.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(line + "\n")
    return row
