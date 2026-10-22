"""Offline HW6 tests; no MongoDB, API key, or live model required."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend import hw06_memory as memory
from backend.hw06_file_memory import consolidate_memory, consolidation_required, handle_command, instruction_following_example


def test_document_validation():
    try:
        memory.DocumentCreate(title="", due_at=datetime.now(timezone.utc))
    except Exception:
        return True
    return False


def test_document_crud():
    memory.store = memory.MongoStore(fallback=memory.MemoryStore())
    created = memory.document_create(memory.DocumentCreate(title="Signal delay", due_at=datetime.now(timezone.utc)))
    fetched = memory.document_get(created["id"])
    updated = memory.document_update(created["id"], memory.DocumentUpdate(status="done"))
    deleted = memory.document_delete(created["id"])
    return fetched is not None and updated["status"] == "done" and deleted and memory.document_get(created["id"]) is None


def test_chat_memory():
    memory.store = memory.MongoStore(fallback=memory.MemoryStore())
    for index in range(10):
        result = memory.chat(memory.ChatRequest(user_id="u1", session_id="s1", message=f"Transit fact {index}"))
        assert result["reply"]
    view = memory.memory_view("u1")
    aggregate = memory.aggregate_view("u1")
    return len(view["messages"]) == 16 and len(view["episodes"]) >= 10 and aggregate["daily_message_counts"]


def test_file_memory():
    text = "# Memory\n\nLast consolidated: 2020-01-01T00:00:00Z\n\n" + "\n".join(["- duplicate fact"] * 45)
    consolidated, conflicts = consolidate_memory(text)
    return consolidation_required(text) and len(consolidated.splitlines()) < len(text.splitlines()) and isinstance(conflicts, list) and "/help" in handle_command("/help") and instruction_following_example(" safe ")["status"] == "ok"


def main():
    tests = [("document validation", test_document_validation), ("document CRUD", test_document_crud), ("chat memory", test_chat_memory), ("file memory", test_file_memory)]
    passed = 0
    for name, function in tests:
        try:
            ok = bool(function())
        except Exception as error:
            ok = False
            print(f"FAIL {name}: {error}")
        if ok:
            passed += 1
            print(f"PASS {name}")
        else:
            print(f"FAIL {name}")
    print(f"{passed}/{len(tests)}")
    return passed == len(tests)


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
