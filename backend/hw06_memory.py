"""HW6 MongoDB document and memory services with an offline test store."""
from __future__ import annotations

import math
import os
import re
import json
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .hw06_database import MemoryStore, MongoStore
from .hw06_models import ChatRequest, DocumentCreate, DocumentResponse, DocumentUpdate
SHORT_TERM_N = int(os.getenv("SHORT_TERM_N", "12"))
SUMMARIZE_EVERY_USER_MSGS = int(os.getenv("SUMMARIZE_EVERY_USER_MSGS", "5"))
EPISODE_TOP_K = int(os.getenv("EPISODE_TOP_K", "3"))


store = MongoStore()


def now() -> datetime:
    return datetime.now(timezone.utc)


def as_json(row: dict[str, Any]) -> dict[str, Any]:
    result = dict(row)
    result["id"] = str(result.pop("_id"))
    return result


def document_create(payload: DocumentCreate) -> dict[str, Any]:
    timestamp = now()
    row = payload.model_dump(mode="json")
    row.update({"created_at": timestamp, "updated_at": timestamp})
    identifier = store.insert("documents", row)
    row["_id"] = identifier
    return as_json(row)


def document_list() -> list[dict[str, Any]]:
    return [as_json(row) for row in store.find("documents", sort=[("created_at", -1)])]


def document_get(identifier: str) -> dict[str, Any] | None:
    query = {"_id": store._mongo_id(identifier)} if store.online else {"_id": identifier}
    rows = store.find("documents", predicate=lambda row: str(row.get("_id")) == identifier, query=query)
    return as_json(rows[0]) if rows else None


def document_update(identifier: str, payload: DocumentUpdate) -> dict[str, Any] | None:
    patch = {key: value for key, value in payload.model_dump(mode="json").items() if value is not None}
    patch["updated_at"] = now()
    row = store.replace("documents", identifier, patch)
    return as_json(row) if row else None


def document_delete(identifier: str) -> bool:
    return store.delete("documents", identifier)


def _words(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9']+", text.lower())


def _token_count(text: str) -> int:
    return max(1, len(_words(text))) if text else 0


def _embedding(text: str) -> list[float]:
    counts = Counter(_words(text))
    terms = sorted(set(counts))[:64]
    vector = [float(counts[term]) for term in terms]
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def _cosine(left: list[float], right: list[float]) -> float:
    length = min(len(left), len(right))
    return sum(left[i] * right[i] for i in range(length))


def _episode_facts(message: str) -> list[str]:
    sentences = [part.strip() for part in re.split(r"[.!?]", message) if part.strip()]
    return sentences[:3]


def _memory_context(user_id: str, session_id: str | None, message: str):
    rows = store.find("messages", query={"user_id": user_id, "session_id": session_id}, sort=[("created_at", -1)], limit=SHORT_TERM_N)
    rows.reverse()
    summaries = store.find("summaries", query={"user_id": user_id}, sort=[("created_at", -1)])
    session_summary = next((row for row in summaries if row.get("scope") == "session" and row.get("session_id") == session_id), None)
    lifetime_summary = next((row for row in summaries if row.get("scope") == "user"), None)
    target = _embedding(message)
    episodes = store.find("episodes", query={"user_id": user_id}, sort=[("created_at", -1)])
    ranked = sorted(episodes, key=lambda row: _cosine(target, row.get("embedding", [])), reverse=True)[:EPISODE_TOP_K]
    return rows, session_summary, lifetime_summary, ranked


def _reply(message: str, context: list[dict[str, Any]], session_summary: dict[str, Any] | None, episodes: list[dict[str, Any]]) -> str:
    if os.getenv("HW6_USE_OLLAMA", "0") == "1":
        try:
            from src.model_client import OllamaModelClient
            prompt = "\n".join(row.get("content", "") for row in context)
            result = OllamaModelClient().complete([("system", "You are a concise municipal transit assistant."), ("user", prompt + "\n" + message)])
            content = getattr(result, "content", str(result))
            if content:
                return str(content)
        except Exception:
            pass
    if session_summary:
        return f"I reviewed your message with the session summary and {len(episodes)} related episodic facts: {message.strip()}"
    return f"Municipal transit assistant response: {message.strip()}"


def chat(payload: ChatRequest) -> dict[str, Any]:
    started = time.perf_counter()
    timestamp = now()
    context, session_summary, lifetime_summary, episodes = _memory_context(payload.user_id, payload.session_id, payload.message)
    store.insert("messages", {"user_id": payload.user_id, "session_id": payload.session_id, "role": "user", "content": payload.message, "created_at": timestamp})
    for fact in _episode_facts(payload.message):
        store.insert("episodes", {"user_id": payload.user_id, "session_id": payload.session_id, "fact": fact[:240], "importance": 0.5, "embedding": _embedding(fact), "created_at": timestamp})
    user_count = len(store.find("messages", query={"user_id": payload.user_id, "session_id": payload.session_id, "role": "user"}))
    if user_count % SUMMARIZE_EVERY_USER_MSGS == 0:
        summary_text = "; ".join(row.get("content", "") for row in context[-SUMMARIZE_EVERY_USER_MSGS:])
        store.insert("summaries", {"user_id": payload.user_id, "session_id": payload.session_id, "scope": "session", "text": summary_text[:1000], "created_at": timestamp})
        session_summaries = store.find("summaries", query={"user_id": payload.user_id, "scope": "session"}, sort=[("created_at", -1)])
        if len(session_summaries) % 3 == 0:
            lifetime = " ".join(row.get("text", "") for row in session_summaries[:3])
            store.insert("summaries", {"user_id": payload.user_id, "session_id": None, "scope": "user", "text": lifetime[:1500], "created_at": timestamp})
    reply = _reply(payload.message, context, session_summary, episodes)
    store.insert("messages", {"user_id": payload.user_id, "session_id": payload.session_id, "role": "assistant", "content": reply, "created_at": now()})
    token_record = {"user_id": payload.user_id, "session_id": payload.session_id, "prompt_tokens": _token_count(payload.message) + sum(_token_count(row.get("content", "")) for row in context), "completion_tokens": _token_count(reply), "system_tokens": 4, "long_term_summary_tokens": _token_count((session_summary or lifetime_summary or {}).get("text", "")), "short_term_tokens": sum(_token_count(row.get("content", "")) for row in context), "episodic_tokens": sum(_token_count(row.get("fact", "")) for row in episodes), "latency_ms": round((time.perf_counter() - started) * 1000, 4), "created_at": now().isoformat()}
    usage_path = Path(__file__).resolve().parents[1] / "reports" / "hw06" / "raw" / "chat_token_usage.jsonl"
    usage_path.parent.mkdir(parents=True, exist_ok=True)
    with usage_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(token_record) + "\n")
    return {"reply": reply, "used": {"short_term_messages": [as_json(row) for row in context], "short_term_count": len(context), "long_term_summary": as_json(session_summary or lifetime_summary) if (session_summary or lifetime_summary) else None, "episodic_facts": [as_json(row) for row in episodes]}}


def memory_view(user_id: str) -> dict[str, Any]:
    messages = store.find("messages", query={"user_id": user_id}, sort=[("created_at", -1)], limit=16)
    summaries = store.find("summaries", query={"user_id": user_id}, sort=[("created_at", -1)])
    episodes = store.find("episodes", query={"user_id": user_id}, sort=[("created_at", -1)], limit=20)
    return {"messages": [as_json(row) for row in messages], "session_summary": next((as_json(row) for row in summaries if row.get("scope") == "session"), None), "lifetime_summary": next((as_json(row) for row in summaries if row.get("scope") == "user"), None), "episodes": [as_json(row) for row in episodes]}


def aggregate_view(user_id: str) -> dict[str, Any]:
    messages = store.find("messages", query={"user_id": user_id})
    counts = Counter((row.get("created_at") or now()).date().isoformat() for row in messages)
    summaries = store.find("summaries", query={"user_id": user_id}, sort=[("created_at", -1)], limit=5)
    return {"daily_message_counts": dict(counts), "recent_summaries": [as_json(row) for row in summaries]}
