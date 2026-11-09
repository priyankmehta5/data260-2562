"""Readable saved HW9 evidence for presentation/screenshots; never reruns experiments."""

import argparse
import json

from backend.hw09_common import RAW, REPORT


def read(name):
    path = RAW / name
    if not path.exists():
        raise SystemExit(f"No completed evidence yet: {name}. Complete the live phase first.")
    return json.loads(path.read_text(encoding="utf-8"))


def show(value):
    print(json.dumps(value, indent=2, ensure_ascii=True))


def answer_text(value):
    try:
        parsed = json.loads(value)
        return parsed.get("answer", value) if isinstance(parsed, dict) else value
    except (ValueError, TypeError):
        return value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "section",
        choices=[
            "counter",
            "cache",
            "performance",
            "thresholds",
            "falsehit",
            "cost",
            "stale",
            "revision",
            "lessons",
            "validation",
            "variants",
            "verify",
        ],
    )
    section = parser.parse_args().section
    print(f"Priyank Mehta - HW9 {section} - saved measured evidence\n")
    if section == "counter":
        result = read("counter.json")
        print("Incident:", result["incident_id"], "Starting count:", result["starting_count"])
        for row in result["records"]:
            print(f"Access #{row['access']:2}: Total = {row['count']:3}; database = {row['database_count']:3}")
    elif section == "cache":
        for index, row in enumerate(read("cache_queries.json"), 1):
            score = "-" if row["similarity"] is None else f"{row['similarity']:.4f}"
            print(f"{index:2} cached={row['is_cached']} cosine={score} latency_ms={row['latency_ms']:.2f}")
            print("   " + row["query"])
    elif section == "revision":
        result = read("revision_sequences.json")[0]
        print("Question:", result["question"])
        print("Controlled initial failure:", result["controlled_initial_failure"])
        for attempt in result["attempts"]:
            print("\nAttempt", attempt["attempt"])
            show(attempt["answer"])
            print("Evaluation:", attempt["evaluation"]["result"])
            print("Feedback:", attempt["evaluation"]["feedback"] or "No revision required")
        print("\nFinal response:", result["final_response"]["answer"])
        print("Attempts:", result["attempt_count"], "Final evaluation:", result["final_result"])
    elif section == "lessons":
        show(json.loads((REPORT / "lessons.json").read_text()))
        later = read("lesson_reuse.json")[0]
        print("Later question:", later["question"])
        print("Loaded lessons:", later["attempts"][0]["loaded_lessons"])
        print("Final answer:", later["final_response"]["answer"])
        print("Evaluation:", later["final_result"])
    elif section == "validation":
        result = read("lesson_validation.json")
        show({key: result[key] for key in ["keep", "reason", "comparisons"]})
    elif section == "stale":
        result = read("stale_invalidation.json")
        print("Record:", result["record_id"], "Question:", result["query"])
        for stage in ["before", "stale_hit", "after_invalidation", "fresh_hit"]:
            row = result[stage]
            print(f"\n{stage}: cached={row['is_cached']}, latency_ms={row['latency_ms']:.2f}")
            print(f"Database version: {row['version']}; cached version: {row['cached_version']}")
            print("Answer:", answer_text(row["answer"]))
        print(result["tradeoff"])
    elif section == "falsehit":
        row = read("false_hit.json")
        print("Cached question:", row["cached_query"])
        print("Incoming question:", row["query"])
        print(f"Similarity: {row['similarity']:.6f}; threshold: {row['threshold']:.2f}")
        print("Returned cached answer:", answer_text(row["answer"]))
        print("Correct answer:", row["correct_answer"])
        print("Explanation:", row["explanation"])
    elif section == "verify":
        result = json.loads((REPORT / "verification.json").read_text())
        show({key: result[key] for key in ["homework", "sid4", "commit_hash", "mode", "timestamp"]})
        artifacts = [check for check in result["checks"] if check["name"].startswith("evidence ")]
        for check in result["checks"]:
            if check["name"].startswith("evidence "):
                continue
            print(("PASS " if check["passed"] else "FAIL ") + check["name"])
        if artifacts:
            print(
                ("PASS " if all(check["passed"] for check in artifacts) else "FAIL ")
                + f"required raw evidence files ({sum(check['passed'] for check in artifacts)}/{len(artifacts)})"
            )
        print(f"Checks passed: {sum(check['passed'] for check in result['checks'])}/{len(result['checks'])}")
        print("overall_pass:", result["overall_pass"])
    elif section == "thresholds":
        print("Threshold  Hit rate  False-hit/all  Mean ms  Total cost")
        for row in read("threshold_summary.json"):
            print(
                f"{row['threshold']:.2f}       {100 * row['hit_rate']:6.2f}%  "
                f"{100 * row['false_hit_rate']:8.2f}%  {row['mean_latency_ms']:8.2f}  {row['total_cost']:.4f}"
            )
        print("False-hit rate denominator: all 40 queries; cost uses declared assumptions.")
    elif section == "variants":
        print("Variant                 Correct Incorrect Avg attempts Avg latency ms")
        for row in read("variant_summary.json"):
            print(
                f"{row['variant']:24} {row['correct']:6} {row['incorrect']:9} "
                f"{row['average_attempts']:12.2f} {row['average_latency_ms']:14.2f}"
            )
    else:
        show(
            read(
                {
                    "performance": "cache_performance.json",
                    "thresholds": "threshold_summary.json",
                    "falsehit": "false_hit.json",
                    "cost": "threshold_choice.json",
                    "variants": "variant_summary.json",
                }[section]
            )
        )


if __name__ == "__main__":
    main()
