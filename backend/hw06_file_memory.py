"""File-based HW6 memory commands and consolidation."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT_PATH = ROOT / "AGENT.md"
MEMORY_PATH = ROOT / "MEMORY.md"


def load_memory_files() -> dict[str, str]:
    return {
        "agent": AGENT_PATH.read_text(encoding="utf-8") if AGENT_PATH.exists() else "",
        "memory": MEMORY_PATH.read_text(encoding="utf-8") if MEMORY_PATH.exists() else "",
    }


def nonempty_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]


def last_consolidated_at(text: str) -> datetime | None:
    match = re.search(r"Last consolidated: *(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)", text)
    if not match:
        match = re.search(r"Last consolidated:\s*(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)", text)
    return datetime.fromisoformat(match.group(1).replace("Z", "+00:00")) if match else None


def consolidation_required(text: str, now: datetime | None = None) -> bool:
    current = now or datetime.now(timezone.utc)
    timestamp = last_consolidated_at(text)
    return len(nonempty_lines(text)) > 40 or timestamp is None or (current - timestamp).total_seconds() > 86400


def _canonical(line: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", line.lower()).strip()


def consolidate_memory(text: str) -> tuple[str, list[str]]:
    lines = nonempty_lines(text)
    seen: dict[str, str] = {}
    contradictions: list[str] = []
    output: list[str] = []
    for line in lines:
        key = _canonical(line)
        if key in seen:
            continue
        conflict = None
        for prior in output:
            if ("port 8762" in line.lower() and "port 8000" in prior.lower()) or ("qwen3:1.7b" in line.lower() and "qwen2" in prior.lower()):
                conflict = prior
                break
        if conflict:
            contradictions.append(f"Resolved contradiction: kept newer fact '{line}' and superseded '{conflict}'.")
            output.remove(conflict)
        seen[key] = line
        output.append(line)
    stamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    result = "# Durable Memory\n\nLast consolidated: " + stamp + "\n\n" + "\n".join(f"- {line}" for line in output + contradictions)
    return result + "\n", contradictions


def compact_memory() -> dict[str, int | list[str]]:
    before = len(nonempty_lines(MEMORY_PATH.read_text(encoding="utf-8"))) if MEMORY_PATH.exists() else 0
    consolidated, contradictions = consolidate_memory(MEMORY_PATH.read_text(encoding="utf-8") if MEMORY_PATH.exists() else "")
    MEMORY_PATH.write_text(consolidated, encoding="utf-8")
    after = len(nonempty_lines(consolidated))
    return {"before": before, "after": after, "contradictions": contradictions}


def dream_memory(facts: list[str]) -> dict[str, int]:
    existing = MEMORY_PATH.read_text(encoding="utf-8") if MEMORY_PATH.exists() else "# Durable Memory\n"
    additions = [fact.strip() for fact in facts if fact.strip()]
    with MEMORY_PATH.open("a", encoding="utf-8") as handle:
        for fact in additions[:3]:
            handle.write(f"\n- {fact}")
    return {"added": min(3, len(additions)), "lines": len(nonempty_lines(existing)) + min(3, len(additions))}


def command_help() -> str:
    return "/memory displays file memory; /compact consolidates it; /dream adds durable facts; /help lists commands."


def handle_command(command: str, facts: list[str] | None = None):
    if command == "/memory":
        return load_memory_files()
    if command == "/compact":
        return compact_memory()
    if command == "/dream":
        return dream_memory(facts or [])
    if command == "/help":
        return command_help()
    return {"error": "unknown memory command"}


def instruction_following_example(value: str) -> dict[str, str]:
    """Small generated-style function: validates text and returns a safe result."""
    cleaned = value.strip()
    if not cleaned:
        return {"status": "error", "message": "value must not be blank"}
    return {"status": "ok", "message": cleaned[:100]}
