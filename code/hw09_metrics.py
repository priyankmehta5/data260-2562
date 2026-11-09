"""Fill report tables only from existing measured records; no synthetic timings."""

import json

from backend.hw09_common import RAW, REPORT


def build():
    lines = [
        "# HW9 measured results",
        "",
        "Configuration: SID4=2562; PORT_BASE=8762; PREFIX=s2562; SEED=2562; "
        "VERIFY_SEED=262562; DOMAIN_ID=2. Model: qwen3:1.7b. "
        "Embeddings: sentence-transformers/all-MiniLM-L6-v2.",
        "",
    ]
    if (RAW / "counter.json").exists():
        counter = json.loads((RAW / "counter.json").read_text())
        end = counter["records"][-1]
        lines += [
            "## Part 1",
            "",
            f"The 25-access run used incident {counter['incident_id']}. Redis advanced from "
            f"{counter['starting_count']} to {end['count']}; MySQL ended at {end['database_count']}. "
            "Each multiple of ten produced a synchronization event. The returned Redis count includes "
            "accesses since the last database checkpoint.",
            "",
        ]
    if (RAW / "cache_performance.json").exists():
        p = json.loads((RAW / "cache_performance.json").read_text())
        lines += [
            "## Part 2",
            "",
            f"Queries: {p['queries']}; hit rate: {100 * p['hit_rate']:.2f}%.",
            f"Cached mean latency: {p['cached_mean_latency_ms']} ms. "
            f"Non-cached mean latency: {p['noncached_mean_latency_ms']} ms.",
            "",
        ]
    if (RAW / "threshold_summary.json").exists():
        rows = json.loads((RAW / "threshold_summary.json").read_text())
        lines += [
            "## Parts 3.2 and 3.4",
            "",
            "False-hit rate = false hits / all 40 cases; the conditional rate among hits is also in raw data.",
            "",
            "| Threshold | Hit rate | False-hit rate | Mean latency (ms) | Total cost |",
            "|---|---|---|---|---|",
        ]
        lines += [
            f"| {r['threshold']:.2f} | {100 * r['hit_rate']:.2f}% | {100 * r['false_hit_rate']:.2f}% | "
            f"{r['mean_latency_ms']:.2f} | {r['total_cost']:.4f} |"
            for r in rows
        ]
        choice = json.loads((RAW / "threshold_choice.json").read_text())
        lines += [
            "",
            "Costs are explicit assumptions, not paid API bills: 0.002 per miss and "
            "0.10 per false hit. A wrong transit answer can require review/rework, budgeted at 50x a local miss.",
            "The miss cost is a flat compute/queue-capacity budget for one local generation. "
            "The false-hit cost is a support/review budget. These values express an assumed preference "
            "for avoiding wrong answers; they are not inferred from latency or real invoices.",
            f"Chosen threshold: {choice['selected']['threshold']:.2f}; minimum assumed cost on this workload.",
            "Each threshold starts with the same ten warmed anchors. Miss answers are not added during the sweep. "
            "Real latency includes the embedding, version read, Redis lookup, and Kafka/model work on misses.",
            "",
        ]
    if (RAW / "false_hit.json").exists():
        false = json.loads((RAW / "false_hit.json").read_text())
        lines += [
            "## Part 3.3 - Full false hit",
            "",
            f"Cached question: {false['cached_query']}",
            f"Incoming question: {false['query']}",
            f"Cosine similarity: {false['similarity']:.6f}; threshold: {false['threshold']:.2f}.",
            f"Returned cached answer: {false['answer']}",
            f"Correct response: {false['correct_answer']}",
            false["explanation"],
            "A shared incident/version marker does not establish that current and historical "
            "questions have the same meaning. A high similarity score is not proof of answer equivalence.",
            "",
        ]
    if (RAW / "stale_invalidation.json").exists():
        stale = json.loads((RAW / "stale_invalidation.json").read_text())
        lines += [
            "## Part 3.5 - Stale answer and invalidation",
            "",
            f"Record: s2562_rel.incidents id={stale['record_id']}. Question: {stale['query']}",
            f"Old answer: {stale['before']['answer']}",
            "After updating the relational record and advancing its version, the disabled-check "
            f"control returned a stale hit: {stale['stale_hit']['answer']}",
            "Re-enabling the version check rejected that cached entry and ran the Kafka/model path: "
            f"{stale['after_invalidation']['answer']}",
            f"Versions at the stale hit: cached={stale['stale_hit']['cached_version']}, "
            f"database={stale['stale_hit']['version']}. The next request hit the refreshed entry.",
            stale["tradeoff"],
            "The demonstration restored the original fixture values afterward, while keeping its version monotonic.",
            "",
        ]
    if (RAW / "variant_summary.json").exists():
        rows = json.loads((RAW / "variant_summary.json").read_text())
        lines += [
            "## Part 4.4",
            "",
            "| Variant | Correct | Incorrect | Average attempts | Average latency (ms) |",
            "|---|---|---|---|---|",
        ]
        lines += [
            f"| {r['variant']} | {r['correct']} | {r['incorrect']} | {r['average_attempts']:.2f} | "
            f"{r['average_latency_ms']:.2f} |"
            for r in rows
        ]
        lines += [
            "",
            "Baseline uses one answer; Evaluator Repair permits two attempts; Lesson Memory adds the "
            "training-derived lesson; Validated Improvement uses only lessons accepted on validation. "
            "Each variant reloads independent state and evaluates the identical held-out inputs.",
            "The controlled incomplete initial answers occur only in the disclosed training demonstration. "
            "Final test answers are actual local-model outputs without injected defects.",
            "The evaluator compares structured facts and requested values in the text against the reference; "
            "it is not a general natural-language entailment checker. Small synthetic datasets limit generalization.",
            "On the held-out set, report any equal accuracy as equal accuracy; a successful controlled repair "
            "demonstrates the workflow but does not by itself establish a general accuracy improvement.",
            "",
        ]
    lines += [
        "## Storage and correctness trade-offs",
        "",
        "Redis INCR is atomic. MySQL stores every tenth count; losing Redis before a checkpoint can lose "
        "up to nine recent views. Concurrent checkpoint writes never reduce the persisted count.",
        "A version read is performed before serving a semantic hit. Changes through the application "
        "increment cache_version. Direct SQL changes must also advance it. Old versions remain stored "
        "but are ineligible; this uses extra storage and a metadata read per request.",
        "Agent communication uses an answer object, deterministic PASS/REVISE feedback, and at most two attempts. "
        "Lessons are selected using training and validation only; held-out test outputs never create lessons.",
    ]
    REPORT.mkdir(parents=True, exist_ok=True)
    (REPORT / "METRICS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Priyank Mehta - METRICS.md updated from completed observations")


if __name__ == "__main__":
    build()
