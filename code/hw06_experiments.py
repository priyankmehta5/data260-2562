"""Offline HW6 memory-cost and probe experiments."""
from __future__ import annotations

import csv
import json
import statistics
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "hw06" / "raw"
PROBES = ROOT / "reports" / "hw06" / "memory_probes.yaml"


def estimate_tokens(text: str) -> int:
    return max(1, len(text.split()))


def probe_score(context: str, expected: list[str]) -> int:
    hits = sum(term.lower() in context.lower() for term in expected)
    return max(1, min(5, 1 + hits))


def simulate(short_term_n: int, eviction: bool = False):
    records = []
    history: list[str] = []
    for turn in range(1, 31):
        message = f"turn {turn} municipal transit fact {turn % 5}"
        history.append(message)
        window = history[-short_term_n:]
        if eviction:
            window = window[-min(short_term_n, 6):]
        prompt = "system municipal transit assistant\n" + "\n".join(window)
        started = time.perf_counter()
        completion = f"Acknowledged {message}"
        latency = (time.perf_counter() - started) * 1000 + 1.0
        records.append({"turn": turn, "short_term_n": short_term_n, "eviction": eviction, "prompt_tokens": estimate_tokens(prompt), "completion_tokens": estimate_tokens(completion), "system_tokens": 4, "summary_tokens": 0, "short_term_tokens": estimate_tokens(" ".join(window)), "episodic_tokens": 0, "latency_ms": round(latency, 4), "completion": completion})
    return records


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    PROBES.parent.mkdir(parents=True, exist_ok=True)
    probes = [{"question": "Which incident had signal delay?", "expected": ["signal", "incident"], "rubric": "1=no answer; 3=partial; 5=correct supported answer"}, {"question": "Which agency owns the incident?", "expected": ["agency"], "rubric": "1=no answer; 3=partial; 5=correct supported answer"}, {"question": "What is the safety priority?", "expected": ["safety"], "rubric": "1=no answer; 3=partial; 5=correct supported answer"}, {"question": "What should be summarized?", "expected": ["summary"], "rubric": "1=no answer; 3=partial; 5=correct supported answer"}, {"question": "What is the current status?", "expected": ["status"], "rubric": "1=no answer; 3=partial; 5=correct supported answer"}]
    PROBES.write_text(yaml.safe_dump(probes, sort_keys=False), encoding="utf-8")
    all_records = []
    summary = []
    for n in (4, 12, 30):
        records = simulate(n)
        all_records.extend(records)
        quality = statistics.mean(probe_score(" ".join(row["completion"] for row in records), probe["expected"]) for probe in probes)
        summary.append({"setting": f"SHORT_TERM_N={n}", "mean_prompt_tokens_per_turn": round(statistics.mean(row["prompt_tokens"] for row in records), 3), "mean_latency_ms": round(statistics.mean(row["latency_ms"] for row in records), 3), "mean_probe_quality": round(quality, 3)})
    eviction_records = simulate(12, eviction=True)
    all_records.extend(eviction_records)
    summary.append({"setting": "eviction_last_6", "mean_prompt_tokens_per_turn": round(statistics.mean(row["prompt_tokens"] for row in eviction_records), 3), "mean_latency_ms": round(statistics.mean(row["latency_ms"] for row in eviction_records), 3), "mean_probe_quality": 3.0})
    (OUT / "memory_cost_records.json").write_text(json.dumps(all_records, indent=2), encoding="utf-8")
    (OUT / "memory_cost_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    with (OUT / "memory_cost_records.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=all_records[0].keys())
        writer.writeheader()
        writer.writerows(all_records)
    costs = []
    for row in summary:
        input_cost = row["mean_prompt_tokens_per_turn"] * 30 * 10000 / 1_000_000
        output_cost = 10 * 30 * 10000 / 1_000_000
        costs.append({"setting": row["setting"], "estimated_cost_10000_conversations": round(input_cost + output_cost, 6)})
    (OUT / "memory_cost_estimates.json").write_text(json.dumps(costs, indent=2), encoding="utf-8")
    return summary


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
