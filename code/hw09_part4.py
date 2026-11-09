"""Training-only lesson derivation, validation gate, then independent held-out variants."""

import hashlib
import json
import statistics

from backend.hw09_agents import (
    AnsweringAgent,
    EvaluatorAgent,
    LessonMemory,
    candidate_lesson,
    run_two_agents,
    validate_lesson,
)
from backend.hw09_common import DATA, RAW, REPORT, event, save
from backend.hw09_model import OllamaAdapter


def run(model=None):
    model = model or OllamaAdapter()
    reference = json.loads((DATA / "reference_data.json").read_text())
    evaluator = EvaluatorAgent(reference)
    training = json.loads((DATA / "training_data.json").read_text())
    validation = json.loads((DATA / "validation_data.json").read_text())
    test_bytes = (DATA / "test_data.json").read_bytes()
    training_runs = [
        run_two_agents(item["question"], AnsweringAgent(model, reference), evaluator, controlled=True)
        for item in training
    ]
    save("revision_sequences.json", training_runs)
    failures = sum(
        any("agency must be" in attempt["evaluation"]["feedback"] for attempt in row["attempts"])
        for row in training_runs
    )
    if failures < 2:
        raise ValueError("Repeated agency failure pattern was not demonstrated")
    lesson = candidate_lesson()
    memory = LessonMemory(REPORT / "lessons.json")
    memory.write([lesson])
    before = [
        run_two_agents(item["question"], AnsweringAgent(model, reference), evaluator, repair=False)
        for item in validation
    ]
    after = [
        run_two_agents(item["question"], AnsweringAgent(model, reference, memory), evaluator, repair=False)
        for item in validation
    ]
    decision = validate_lesson(before, after)
    save("lesson_validation.json", {"before": before, "after": after, **decision})
    selected = memory.read() if decision["keep"] else []
    memory.write(selected)
    save("selected_lessons.json", selected)
    # Freeze selection BEFORE reading any held-out question.
    save(
        "selection_provenance.json",
        {
            "test_sha256": hashlib.sha256(test_bytes).hexdigest(),
            "selected_lessons": selected,
            "source": "training and validation only",
        },
    )
    test = json.loads(test_bytes)
    summaries, all_runs = [], []
    for variant in ["Baseline", "Evaluator Repair", "Lesson Memory", "Validated Improvement"]:
        variant_memory = None
        if variant in ("Lesson Memory", "Validated Improvement"):
            variant_memory = LessonMemory(RAW / "state" / f"{variant.replace(' ', '_')}_lessons.json")
            variant_memory.write([dict(lesson)] if variant == "Lesson Memory" else selected)
        answering = AnsweringAgent(model, reference, variant_memory)
        rows = [run_two_agents(item["question"], answering, evaluator, repair=variant != "Baseline") for item in test]
        all_runs.append({"variant": variant, "runs": rows})
        correct = sum(row["final_result"] == "PASS" for row in rows)
        summaries.append(
            {
                "variant": variant,
                "correct": correct,
                "incorrect": len(rows) - correct,
                "average_attempts": statistics.mean(row["attempt_count"] for row in rows),
                "average_latency_ms": statistics.mean(row["latency_ms"] for row in rows),
            }
        )
    assert test_bytes == (DATA / "test_data.json").read_bytes()
    save("variant_runs.json", all_runs)
    save("variant_summary.json", summaries)
    save("lesson_reuse.json", [row for row in after if any(a["loaded_lessons"] for a in row["attempts"])])
    event("Part 4 complete", summaries=summaries, lesson_retained=decision["keep"])
    return summaries


if __name__ == "__main__":
    run()
