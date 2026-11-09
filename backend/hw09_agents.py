"""Two agents, deterministic reference evaluator, persisted lessons, and two-attempt bound."""

import json
import re
import time
from pathlib import Path

from .hw09_common import event, now


def reference_for(question, reference):
    match = re.search(r"\broute\s+(\d+)\b", question, re.I)
    record = next((row for row in reference["records"] if match and row["route"] == int(match[1])), None)
    if record is None or "yesterday" in question.lower():
        return {}
    requested = {}
    for word, key in [("severity", "severity"), ("delay", "delay_minutes"), ("status", "status"), ("agency", "agency")]:
        if word in question.lower():
            requested[key] = record[key]
    return requested


class EvaluatorAgent:
    def __init__(self, reference):
        self.reference = reference

    def evaluate(self, question, answer):
        expected = reference_for(question, self.reference)
        facts = answer.get("facts", {})
        if not expected:
            passed = answer.get("abstained") is True and not facts
            errors = [] if passed else ["Unsupported question: abstain without supplying facts."]
        else:
            errors = [f"{key} must be {value}" for key, value in expected.items() if facts.get(key) != value]
            route = re.search(r"\broute\s+(\d+)\b", question, re.I)
            full = next(row for row in self.reference["records"] if row["route"] == int(route[1]))
            errors += [
                f"Unsupported fact {key}={value}"
                for key, value in facts.items()
                if key not in full or full[key] != value
            ]
            # Text must also contain the requested values; structured facts cannot hide an empty answer.
            errors += [
                f"Answer text omits {key}"
                for key, value in expected.items()
                if str(value).lower() not in answer.get("answer", "").lower()
            ]
            passed = not errors and answer.get("abstained") is not True
        return {
            "result": "PASS" if passed else "REVISE",
            "explanation": "All requested facts agree with the reference." if passed else "; ".join(errors),
            "feedback": "" if passed else "; ".join(errors),
            "expected_facts": expected,
        }


class LessonMemory:
    def __init__(self, path):
        self.path = Path(path)

    def read(self):
        return json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else []

    def write(self, lessons):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(lessons, indent=2), encoding="utf-8")

    def relevant(self, question):
        lessons = self.read()
        selected = []
        for lesson in lessons:
            if "agency" in question.lower() and "agency" in lesson["failure_pattern"].lower():
                lesson["use_count"] += 1
                selected.append(dict(lesson))
        self.write(lessons)
        return selected


class AnsweringAgent:
    def __init__(self, model, reference, memory=None):
        self.model, self.reference, self.memory = model, reference, memory

    def answer(self, question, feedback="", controlled=False):
        lessons = self.memory.relevant(question) if self.memory else []
        answer = self.model.generate(
            question, self.reference, " ".join(item["correction"] for item in lessons), feedback
        )
        if controlled and not feedback:
            # Explicitly disclosed fault injection, solely for the required training demonstration.
            answer = {"answer": "The incident severity is 3.", "facts": {"severity": 3}, "abstained": False}
        return answer, [item["lesson_id"] for item in lessons]


def run_two_agents(question, answering, evaluator, repair=True, controlled=False):
    started = time.perf_counter()
    attempts, feedback = [], ""
    for index in range(1, 3 if repair else 2):
        answer, lessons = answering.answer(question, feedback, controlled)
        evaluation = evaluator.evaluate(question, answer)
        row = {"attempt": index, "answer": answer, "evaluation": evaluation, "loaded_lessons": lessons}
        attempts.append(row)
        event("answer_evaluated", question=question, **row)
        if evaluation["result"] == "PASS":
            break
        feedback = evaluation["feedback"]
    return {
        "question": question,
        "attempts": attempts,
        "attempt_count": len(attempts),
        "final_response": attempts[-1]["answer"],
        "final_result": attempts[-1]["evaluation"]["result"],
        "stop_reason": "passed" if attempts[-1]["evaluation"]["result"] == "PASS" else "attempt_limit",
        "controlled_initial_failure": controlled,
        "latency_ms": (time.perf_counter() - started) * 1000,
    }


def candidate_lesson():
    return {
        "lesson_id": "agency-completeness-001",
        "failure_pattern": "Compound answers omit the agency.",
        "correction": "When agency is requested with severity, include both the agency and severity "
        "from the reference in the facts object and answer text. Abstain outside the reference.",
        "created_at": now(),
        "use_count": 0,
    }


def validate_lesson(before, after):
    comparisons = []
    for old, new in zip(before, after, strict=True):
        if old["question"] != new["question"]:
            raise ValueError("Validation question order changed")
        comparisons.append(
            {
                "question": old["question"],
                "before": old["final_result"],
                "after": new["final_result"],
                "regression": old["final_result"] == "PASS" and new["final_result"] != "PASS",
            }
        )
    return {
        "keep": not any(row["regression"] for row in comparisons),
        "comparisons": comparisons,
        "reason": "No previously correct answer regressed; failure cases did not worsen."
        if not any(row["regression"] for row in comparisons)
        else "Reject lesson: validation regression.",
    }
