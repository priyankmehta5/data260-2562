"""Offline behavioral tests; fixtures never certify live Redis, Kafka, or Ollama."""

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
from sqlalchemy import create_engine, text

from backend.hw09_agents import (
    AnsweringAgent,
    EvaluatorAgent,
    LessonMemory,
    candidate_lesson,
    reference_for,
    run_two_agents,
    validate_lesson,
)
from backend.hw09_cache import SemanticCache
from backend.hw09_common import DATA
from backend.hw09_database import IncidentDatabaseWithCache


class MemoryRedis:
    def __init__(self):
        self.values = {}

    def exists(self, key):
        return key in self.values

    def setnx(self, key, value):
        self.values.setdefault(key, value)

    def incr(self, key):
        self.values[key] = int(self.values.get(key, 0)) + 1
        return self.values[key]

    def get(self, key):
        return self.values.get(key)

    def hset(self, key, mapping):
        self.values[key] = mapping

    def delete(self, key):
        self.values.pop(key, None)

    def scan_iter(self, match):
        return [key for key in self.values if key.startswith(match[:-1])]

    def ft(self, index):
        client = self

        class Index:
            def create_index(self, *args, **kwargs):
                self.definition = kwargs

            def search(self, query, query_params):
                vector = np.frombuffer(query_params["vector"], dtype=np.float32)
                rows = []
                scope = index.split(":")[-1]
                for key, value in client.values.items():
                    if key.startswith(f"s2562:semantic:{scope}:"):
                        other = np.frombuffer(value["embedding"], dtype=np.float32)
                        distance = 1 - float(vector @ other / (np.linalg.norm(vector) * np.linalg.norm(other)))
                        rows.append(SimpleNamespace(distance=distance, **value))
                return SimpleNamespace(docs=sorted(rows, key=lambda row: row.distance))

        return Index()


class Model:
    def __init__(self, reference, always_wrong=False):
        self.reference, self.calls, self.always_wrong = reference, [], always_wrong

    def generate(self, question, context, instructions="", feedback=""):
        self.calls.append({"question": question, "instructions": instructions, "feedback": feedback})
        facts = reference_for(question, self.reference)
        if self.always_wrong:
            return {"answer": "Unknown", "facts": {}, "abstained": False}
        return {
            "answer": ", ".join(f"{key} {value}" for key, value in facts.items()) or "No reference facts.",
            "facts": facts,
            "abstained": not facts,
        }


class CounterTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        with self.engine.begin() as c:
            c.execute(
                text(
                    "CREATE TABLE incidents (id INT PRIMARY KEY, title TEXT, description TEXT, "
                    "severity INT, agency_id INT, view_count INT, cache_version INT)"
                )
            )
            c.execute(text("INSERT INTO incidents VALUES(1,'Signal','Demo',3,1,0,0)"))
        self.redis = MemoryRedis()
        self.database = IncidentDatabaseWithCache(self.engine, self.redis)

    def tearDown(self):
        self.engine.dispose()

    def test_25_accesses_sync_at_ten_and_twenty(self):
        observed = []
        for _ in range(25):
            self.database.increment_incident_views(1)
            observed.append(self.database.incident(1)["view_count"])
        self.assertEqual(observed, [0] * 9 + [10] * 10 + [20] * 6)
        self.assertEqual(self.redis.get("s2562:views:incident:1"), 25)

    def test_cold_cache_resumes_persisted_count(self):
        with self.engine.begin() as c:
            c.execute(text("UPDATE incidents SET view_count=30 WHERE id=1"))
        self.assertEqual(self.database.increment_incident_views(1), 31)

    def test_missing_or_invalid_incident_does_not_increment(self):
        for value in [True, 0, -1, "1", 99]:
            with self.assertRaises(ValueError):
                self.database.increment_incident_views(value)
        self.assertEqual(self.redis.values, {})


class CacheTests(unittest.IsolatedAsyncioTestCase):
    async def test_miss_hit_and_version_rejection_skip_pipeline(self):
        db = SimpleNamespace(version="incident-1-v0")
        db.context = lambda question: {"record": {"id": 1}, "version": db.version}
        embedder = SimpleNamespace(encode=lambda q: (np.ones(384) / np.sqrt(384)).astype(np.float32))

        class Pipeline:
            calls = 0

            async def answer(self, question, context):
                self.calls += 1
                return {"answer": f"answer-{context['version']}", "correlation_id": str(self.calls)}

        pipeline, client = Pipeline(), MemoryRedis()
        cache = SemanticCache(client, embedder, db, pipeline)
        first = await cache.query("Route 2 severity")
        hit = await cache.query("Route 2 severity")
        self.assertFalse(first["is_cached"])
        self.assertTrue(hit["is_cached"])
        self.assertAlmostEqual(hit["similarity"], 1, places=5)
        self.assertEqual(pipeline.calls, 1)
        db.version = "incident-1-v1"
        stale = await cache.query("Route 2 severity", enforce_version=False)
        self.assertTrue(stale["is_cached"])
        fresh = await cache.query("Route 2 severity")
        self.assertFalse(fresh["is_cached"])
        self.assertNotEqual(fresh["answer"], stale["answer"])
        self.assertEqual(pipeline.calls, 2)

    async def test_scope_clear_preserves_other_keys(self):
        client = MemoryRedis()
        client.values = {"s2562:semantic:one:x": {}, "s2562:semantic:two:x": {}, "other:key": 2}
        SemanticCache(client, None, None, None, "one").clear()
        self.assertEqual(set(client.values), {"s2562:semantic:two:x", "other:key"})


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.reference = json.loads((DATA / "reference_data.json").read_text())
        self.evaluator = EvaluatorAgent(self.reference)

    def test_feedback_repairs_controlled_failure(self):
        model = Model(self.reference)
        result = run_two_agents(
            "What is the severity and agency of the Route 2 incident?",
            AnsweringAgent(model, self.reference),
            self.evaluator,
            controlled=True,
        )
        self.assertEqual([a["evaluation"]["result"] for a in result["attempts"]], ["REVISE", "PASS"])
        self.assertTrue(model.calls[1]["feedback"])

    def test_never_exceeds_two_attempts(self):
        result = run_two_agents(
            "What is the severity of the Route 2 incident?",
            AnsweringAgent(Model(self.reference, True), self.reference),
            self.evaluator,
        )
        self.assertEqual(result["attempt_count"], 2)
        self.assertEqual(result["stop_reason"], "attempt_limit")

    def test_lesson_saved_reloaded_and_used(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "lessons.json"
            LessonMemory(path).write([candidate_lesson()])
            model = Model(self.reference)
            memory = LessonMemory(path)
            AnsweringAgent(model, self.reference, memory).answer("State severity and agency of Route 4.")
            self.assertIn("agency", model.calls[0]["instructions"])
            self.assertEqual(memory.read()[0]["use_count"], 1)

    def test_unsupported_answer_rejected(self):
        result = self.evaluator.evaluate(
            "How do I bake bread?", {"facts": {"severity": 3}, "answer": "Severity 3", "abstained": False}
        )
        self.assertEqual(result["result"], "REVISE")

    def test_validation_rejects_regression(self):
        decision = validate_lesson(
            [{"question": "q", "final_result": "PASS"}], [{"question": "q", "final_result": "REVISE"}]
        )
        self.assertFalse(decision["keep"])

    def test_text_must_contain_fact_values(self):
        result = self.evaluator.evaluate(
            "What is the severity of Route 2?",
            {"facts": {"severity": 3}, "answer": "A delay exists", "abstained": False},
        )
        self.assertEqual(result["result"], "REVISE")

    def test_no_answers_in_input_splits(self):
        for split in ["training", "validation", "test"]:
            rows = json.loads((DATA / f"{split}_data.json").read_text())
            self.assertTrue(all(set(row) == {"id", "question"} for row in rows))


if __name__ == "__main__":
    with patch("backend.hw09_cache.event"), patch("backend.hw09_agents.event"), patch("backend.hw09_database.event"):
        unittest.main(verbosity=2)
