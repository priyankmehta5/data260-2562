"""Real Redis/MySQL/Kafka/Ollama experiments; sweep blocked until labeled cases are committed."""

import asyncio
import hashlib
import json
import statistics
import subprocess

import redis
import yaml

from backend.database import engine
from backend.hw09_agents import reference_for
from backend.hw09_cache import Embedder, SemanticCache
from backend.hw09_common import DATA, RAW, REDIS_URL, ROOT, save
from backend.hw09_database import IncidentDatabaseWithCache
from backend.hw09_pipeline import KafkaAnswerPipeline


def committed_cases():
    content = (ROOT / "cache_cases.yaml").read_bytes()
    frozen = json.loads((RAW / "dataset_manifest.json").read_text())["cache_cases_sha256"]
    if hashlib.sha256(content).hexdigest() != frozen:
        raise ValueError("Frozen labels changed; document a correction separately, never relabel after results")
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    committed = subprocess.run(["git", "show", f"{revision}:cache_cases.yaml"], cwd=ROOT, capture_output=True)
    # Normalize checkout line endings without silently accepting label changes.
    if committed.returncode or committed.stdout.replace(b"\r\n", b"\n") != content.replace(b"\r\n", b"\n"):
        raise RuntimeError("MANUAL CHECKPOINT: commit cache_cases.yaml in GitHub Desktop before the threshold sweep")
    return {"commit": revision, "sha256": frozen}


def resources():
    client = redis.Redis.from_url(REDIS_URL)
    client.ping()
    database = IncidentDatabaseWithCache(engine, client)
    embedder = Embedder()
    embedder.encode("Embedding warmup excluded from measured calls")
    return client, database, embedder, KafkaAnswerPipeline()


def metrics(rows):
    hits = [row for row in rows if row["is_cached"]]
    misses = [row for row in rows if not row["is_cached"]]
    return {
        "queries": len(rows),
        "hits": len(hits),
        "misses": len(misses),
        "hit_rate": len(hits) / len(rows),
        "cached_mean_latency_ms": statistics.mean(r["latency_ms"] for r in hits) if hits else None,
        "noncached_mean_latency_ms": statistics.mean(r["latency_ms"] for r in misses) if misses else None,
    }


async def baseline():
    client, database, embedder, pipeline = resources()
    try:
        context = database.context("Route 2 incident")
        incident_id = context["record"]["id"]
        # Dedicated counter fixture; never zero an existing user's count.
        key = f"s2562:views:incident:{incident_id}"
        start = int(client.get(key) or database.incident(incident_id)["view_count"])
        counter = []
        for access in range(1, 26):
            count = database.increment_incident_views(incident_id)
            db_count = database.incident(incident_id)["view_count"]
            counter.append({"access": access, "count": count, "database_count": db_count})
            print(f"Priyank Mehta Access #{access}: Total = {count}; database = {db_count}", flush=True)
        save("counter.json", {"incident_id": incident_id, "starting_count": start, "records": counter})
        cache = SemanticCache(client, embedder, database, pipeline, "baseline")
        cache.clear()
        questions = [
            "What is the current severity of the Route 2 incident?",
            "What is the current severity of the Route 2 incident?",
            "Tell me the current severity for the incident on Route 2.",
            "What is the current delay of the Route 3 incident?",
            "What is the current delay of the Route 3 incident?",
            "Tell me the current delay for the incident on Route 3.",
            "What is the current status of the Route 4 incident?",
            "What is the current status of the Route 4 incident?",
            "Tell me the current status for the incident on Route 4.",
            "What is the current severity of the Route 5 incident?",
            "How do I bake sourdough bread?",
            "Explain photosynthesis.",
        ]
        rows = [await cache.query(question) for question in questions]
        save("cache_queries.json", rows)
        save("cache_performance.json", metrics(rows))
    finally:
        client.close()


async def stale_demo(client, database, embedder, pipeline):
    cache = SemanticCache(client, embedder, database, pipeline, "stale")
    cache.clear()
    question = "What is the current severity of the Route 2 incident?"
    original = database.context(question)["record"]
    first = await cache.query(question)
    try:
        database.update_fixture(
            original["id"],
            5 if original["severity"] != 5 else 2,
            "Synthetic HW9 update: signal escalation; delay 30 minutes; status open.",
        )
        stale = await cache.query(question, enforce_version=False)
        fresh = await cache.query(question, enforce_version=True)
        hit = await cache.query(question)
        save(
            "stale_invalidation.json",
            {
                "query": question,
                "record_id": original["id"],
                "before": first,
                "stale_hit": stale,
                "after_invalidation": fresh,
                "fresh_hit": hit,
                "strategy": "Compare cached record/version with the current MySQL version before serving a hit.",
                "tradeoff": "A metadata database read per request and obsolete vectors consume work/storage; "
                "updates must advance cache_version. Snapshot is valid as of the version read.",
            },
        )
    finally:
        database.update_fixture(original["id"], original["severity"], original["description"])


async def sweep():
    provenance = committed_cases()  # MUST run before embedding/search or any threshold result.
    save("sweep_provenance.json", provenance)
    cases = yaml.safe_load((ROOT / "cache_cases.yaml").read_text())
    reference = json.loads((DATA / "reference_data.json").read_text())
    client, database, embedder, pipeline = resources()
    records, summaries, seeds = [], [], []
    try:
        # Warm anchors once through the real model/Kafka path; identical corpus for every threshold.
        for anchor in cases["anchors"]:
            context = database.context(anchor["query"])
            output = await pipeline.answer(anchor["query"], context)
            seeds.append({**anchor, "answer": output["answer"], "version": context["version"]})
        save("cache_anchors.json", seeds)
        false_hit = None
        for threshold in [0.75, 0.80, 0.85, 0.90, 0.95]:
            cache = SemanticCache(client, embedder, database, pipeline, f"sweep{int(threshold * 100)}", threshold)
            cache.clear()
            for anchor in seeds:
                cache.store(anchor["query"], embedder.encode(anchor["query"]), anchor["answer"], anchor["version"])
            rows = []
            for case in cases["cases"]:
                result = await cache.query(case["query"], store_miss=False)
                row = {
                    **case,
                    **result,
                    "threshold": threshold,
                    "false_hit": result["is_cached"] and not case["should_hit"],
                }
                rows.append(row)
                records.append(row)
                save("threshold_records.json", records)  # preserve completed calls if interrupted
                if row["false_hit"] and false_hit is None:
                    false_hit = {
                        **row,
                        "correct_facts": reference_for(case["query"], reference),
                        "correct_answer": "The reference does not supply historical facts; abstain."
                        if case["category"] == "similar_different"
                        else "Outside the transit reference; abstain.",
                        "explanation": "The queries share entity and attribute wording; the embedding "
                        "underweights the temporal change from current to yesterday.",
                    }
            false_hits = sum(row["false_hit"] for row in rows)
            misses = sum(not row["is_cached"] for row in rows)
            summaries.append(
                {
                    "threshold": threshold,
                    **metrics(rows),
                    "false_hits": false_hits,
                    "false_hit_rate": false_hits / len(rows),
                    "false_hit_rate_among_hits": false_hits / sum(r["is_cached"] for r in rows)
                    if any(r["is_cached"] for r in rows)
                    else 0,
                    "mean_latency_ms": statistics.mean(r["latency_ms"] for r in rows),
                    "total_cost": round(misses * 0.002 + false_hits * 0.10, 4),
                }
            )
        save("threshold_summary.json", summaries)
        if false_hit is None:
            raise RuntimeError("No false hit observed; preserve labels and document a separate exploratory example")
        save("false_hit.json", false_hit)
        choice = min(summaries, key=lambda r: (r["total_cost"], r["false_hits"], -r["threshold"]))
        save(
            "threshold_choice.json",
            {
                "selected": choice,
                "miss_cost": 0.002,
                "false_hit_support_cost": 0.10,
                "units": "assumed service-cost units, not Ollama billing",
                "justification": "A wrong transit answer can trigger review/rework; budget 50x a local inference miss.",
                "selection": "Minimum assumed total cost; prefer fewer false hits and then stricter threshold on ties.",
                "limitation": "Selected on this labeled workload, not proof of production accuracy.",
            },
        )
        await stale_demo(client, database, embedder, pipeline)
    finally:
        client.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["baseline", "sweep"])
    args = parser.parse_args()
    asyncio.run(baseline() if args.phase == "baseline" else sweep())
