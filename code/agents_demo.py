import argparse
import json
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.model_client import OllamaModelClient


STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "because", "been",
    "by", "for", "from", "has", "have", "in", "into", "is", "it",
    "of", "on", "or", "that", "the", "their", "this", "to", "was",
    "were", "will", "with",
}


def clean_text(value: Any) -> str:
    text = str(value or "")
    text = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE)
    text = text.replace("```", "").replace("`", "")
    return " ".join(text.split())


def extract_json(text: str) -> dict[str, Any]:
    cleaned = clean_text(text)
    decoder = json.JSONDecoder()

    for index, character in enumerate(cleaned):
        if character != "{":
            continue

        try:
            value, _ = decoder.raw_decode(cleaned[index:])
            if isinstance(value, dict):
                return value
        except json.JSONDecodeError:
            continue

    return {}


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)?", text.lower())


def phrase_candidates(
    title: str,
    content: str,
    limit: int = 15,
) -> list[str]:
    words = [
        word
        for word in tokenize(f"{title} {content}")
        if word not in STOP_WORDS and len(word) > 2
    ]

    phrases = []

    for size in (3, 2):
        for index in range(len(words) - size + 1):
            phrases.append(" ".join(words[index:index + size]))

    counts = Counter(phrases)
    first_position = {}

    for index, phrase in enumerate(phrases):
        first_position.setdefault(phrase, index)

    ranked = sorted(
        counts,
        key=lambda phrase: (-counts[phrase], first_position[phrase]),
    )

    candidates = ranked[:limit]

    for word in words:
        if word not in candidates:
            candidates.append(word)

        if len(candidates) >= limit:
            break

    return candidates


def normalize_tag(tag: Any) -> str:
    value = clean_text(tag).lower()
    value = re.sub(r"[^a-z0-9 -]", "", value)
    return " ".join(value.split()[:4])


def normalize_summary(summary: Any, title: str, content: str) -> str:
    value = clean_text(summary)

    if not value:
        value = clean_text(f"{title}. {content}")

    words = value.split()

    if len(words) > 25:
        value = " ".join(words[:25])

    value = value.rstrip(".,;:!?")

    if not value:
        value = title.strip()

    return f"{value}."


def coerce_reply(
    raw_reply: Any,
    title: str,
    content: str,
    strict: bool,
) -> dict[str, Any]:
    reply = raw_reply if isinstance(raw_reply, dict) else {}
    data = reply.get("data", {})

    if not isinstance(data, dict):
        data = {}

    source_words = set(tokenize(f"{title} {content}"))
    tags = []

    raw_tags = data.get("tags", [])

    if not isinstance(raw_tags, list):
        raw_tags = []

    for raw_tag in raw_tags:
        tag = normalize_tag(raw_tag)

        if not tag or tag in tags:
            continue

        if strict and not source_words.intersection(tokenize(tag)):
            continue

        tags.append(tag)

        if len(tags) == 3:
            break

    for candidate in phrase_candidates(title, content):
        tag = normalize_tag(candidate)

        if tag and tag not in tags:
            tags.append(tag)

        if len(tags) == 3:
            break

    if len(tags) < 3:
        raise ValueError("The input does not contain enough words for three tags.")

    issues = data.get("issues", [])

    if not isinstance(issues, list):
        issues = [clean_text(issues)]

    return {
        "thought": clean_text(reply.get("thought", "")),
        "message": clean_text(reply.get("message", "")),
        "data": {
            "tags": tags[:3],
            "summary": normalize_summary(
                data.get("summary", ""),
                title,
                content,
            ),
            "issues": [
                clean_text(issue)
                for issue in issues
                if clean_text(issue)
            ],
        },
    }


def call_agent(
    client: OllamaModelClient,
    system_prompt: str,
    user_prompt: str,
    title: str,
    content: str,
    strict: bool,
) -> tuple[dict[str, Any], int]:
    started = time.perf_counter()

    response = client.complete(
        [
            ("system", system_prompt),
            ("human", user_prompt),
        ]
    )

    latency_ms = round((time.perf_counter() - started) * 1000)
    parsed = extract_json(str(response.content))
    result = coerce_reply(parsed, title, content, strict)

    return result, latency_ms


def finalize(
    planner: dict[str, Any],
    reviewer: dict[str, Any],
    title: str,
    content: str,
) -> dict[str, Any]:
    reviewed = coerce_reply(reviewer, title, content, True)

    if len(reviewed["data"]["tags"]) != 3:
        reviewed = coerce_reply(planner, title, content, True)

    return {
        "tags": reviewed["data"]["tags"],
        "summary": reviewed["data"]["summary"],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--title", required=True)
    parser.add_argument("--content", required=True)
    parser.add_argument(
        "--model",
        default=os.environ.get("OLLAMA_MODEL", "qwen3:1.7b"),
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get(
            "OLLAMA_URL",
            "http://localhost:11434",
        ),
    )
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    client = OllamaModelClient(
        model=args.model,
        temperature=args.temperature,
        base_url=args.base_url,
    )

    planner_system = (
        "You are the Planner agent. Create exactly three distinct topical "
        "tags and one sentence summarizing the supplied title and content. "
        "The summary must contain no more than 25 words. Derive everything "
        "from the supplied input. Return only valid JSON with keys thought, "
        "message, and data. Data must contain tags, summary, and issues."
    )

    planner_prompt = (
        f"Title: {args.title}\n"
        f"Content: {args.content}\n\n"
        "Return this JSON structure:\n"
        "{"
        '"thought":"brief decision note",'
        '"message":"planner result",'
        '"data":{'
        '"tags":["tag one","tag two","tag three"],'
        '"summary":"one sentence",'
        '"issues":[]'
        "}"
        "}"
    )

    planner, planner_latency = call_agent(
        client,
        planner_system,
        planner_prompt,
        args.title,
        args.content,
        args.strict,
    )

    reviewer_system = (
        "You are the Reviewer agent. Review the Planner output against the "
        "original input. Correct generic, repeated, or unrelated tags. "
        "Ensure there are exactly three topical tags and the summary is one "
        "sentence of no more than 25 words. Return only valid JSON with keys "
        "thought, message, and data. Data must contain the corrected tags, "
        "summary, and issues."
    )

    reviewer_prompt = (
        f"Original title: {args.title}\n"
        f"Original content: {args.content}\n\n"
        f"Planner output:\n{json.dumps(planner, indent=2)}\n\n"
        "Return the reviewed result using the same JSON structure."
    )

    reviewer, reviewer_latency = call_agent(
        client,
        reviewer_system,
        reviewer_prompt,
        args.title,
        args.content,
        args.strict,
    )

    final_output = finalize(
        planner,
        reviewer,
        args.title,
        args.content,
    )

    transcript = {
        "planner": planner,
        "reviewer": reviewer,
    }

    publish_output = {
        "title": args.title,
        "content": args.content,
        "transcript": transcript,
        "final": final_output,
    }

    print(
        f"\n--- Planner Output ({planner_latency} ms) ---"
    )
    print(json.dumps(planner, indent=2))

    print(
        f"\n--- Reviewer Output ({reviewer_latency} ms) ---"
    )
    print(json.dumps(reviewer, indent=2))

    print("\n--- Finalized Output ---")
    print(json.dumps(final_output, indent=2))

    print("\n--- Publish Output ---")
    print(json.dumps(publish_output, indent=2))


if __name__ == "__main__":
    main()