"""Offline behavioral tests. These do not count as Kafka integration evidence."""

import asyncio
import copy
import tempfile
import unittest
from pathlib import Path
from uuid import UUID, uuid4

from backend.hw08_agents import DedupStore, transform
from backend.hw08_common import RESPONSES, TASKS, TOPICS
from backend.hw08_incidents import IncidentService
from backend.hw08_rpc import KafkaRPC, make_request

DATA = {
    "title": "Signal delay",
    "description": "Delay requires operations review",
    "incident_code": "HW8-2562",
    "severity": 3,
    "agency_id": 1,
}


class IncidentTests(unittest.TestCase):
    def setUp(self):
        self.service = IncidentService()

    def test_create_get_and_uuid(self):
        response = self.service.process(make_request("CREATE_INCIDENT", DATA))
        self.assertTrue(response["success"])
        UUID(response["incident_id"])
        request = make_request("GET_INCIDENT", {"incident_id": response["incident_id"]})
        found = self.service.process(request)
        self.assertEqual(found["correlation_id"], request["correlation_id"])
        self.assertEqual(found["incident"], {"incident_id": response["incident_id"], **DATA})

    def test_duplicate_has_one_side_effect(self):
        request = make_request("CREATE_INCIDENT", DATA)
        first = self.service.process(request)
        self.assertEqual(first, self.service.process(request))
        self.assertEqual(len(self.service.incidents), 1)

    def test_conflicting_correlation_is_rejected(self):
        request = make_request("CREATE_INCIDENT", DATA)
        self.service.process(request)
        request["data"] = {**DATA, "severity": 4}
        self.assertFalse(self.service.process(request)["success"])
        self.assertEqual(len(self.service.incidents), 1)

    def test_required_fields_missing(self):
        for field in DATA:
            with self.subTest(field=field):
                values = dict(DATA)
                del values[field]
                self.assertFalse(self.service.process(make_request("CREATE_INCIDENT", values))["success"])

    def test_invalid_and_empty_values(self):
        for patch in (
            {"title": "   "},
            {"description": ""},
            {"severity": True},
            {"severity": 6},
            {"severity": "3"},
            {"agency_id": 0},
            {"incident_code": "!"},
            {"extra": 5},
        ):
            with self.subTest(patch=patch):
                self.assertFalse(self.service.process(make_request("CREATE_INCIDENT", {**DATA, **patch}))["success"])

    def test_unknown_operation_and_missing_id(self):
        for request in (
            make_request("DELETE_INCIDENT", {}),
            make_request("GET_INCIDENT", {"incident_id": str(uuid4())}),
            make_request("GET_INCIDENT", {}),
            make_request("GET_INCIDENT", {"incident_id": 7}),
        ):
            response = self.service.process(request)
            self.assertFalse(response["success"])
            self.assertEqual(response["correlation_id"], request["correlation_id"])

    def test_invalid_envelope(self):
        for request in (
            {},
            {"correlation_id": " "},
            {"correlation_id": "x", "reply_to": "bad"},
            {"correlation_id": "x", "reply_to": RESPONSES, "data": []},
        ):
            self.assertFalse(self.service.process(request)["success"])

    def test_exact_topic_configuration(self):
        self.assertEqual(len(TOPICS), 7)
        self.assertEqual(TOPICS[TASKS], 2)
        self.assertTrue(all(topic.startswith("s2562_") for topic in TOPICS))


class PipelineTests(unittest.TestCase):
    def test_all_stages_preserve_id(self):
        message = {"correlation_id": str(uuid4()), "question": "How to review transit incidents?"}
        original = copy.deepcopy(message)
        for stage in ("planner", "writer", "reviewer"):
            message = transform(stage, message)
            self.assertEqual(message["correlation_id"], original["correlation_id"])
        self.assertEqual(message["status"], "approved")
        self.assertTrue(message["answer"])
        self.assertNotIn("plan", original)

    def test_poison_message_rejected(self):
        with self.assertRaises(ValueError):
            transform("writer", {"correlation_id": "poison", "question": 4})

    def test_persistent_deduplication_and_conflict(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "state.sqlite3"
            store = DedupStore(file)
            message = {"correlation_id": "one", "question": "Review incident", "plan": ["review"]}
            output = transform("writer", message)
            store.save("group", message, output)
            store.db.close()
            restored = DedupStore(file)
            self.assertEqual(restored.get("group", message), output)
            self.assertIsNone(restored.get("another-group", message))
            with self.assertRaises(ValueError):
                restored.get("group", {**message, "question": "changed"})
            restored.db.close()

    def test_rpc_timeout_removes_pending(self):
        class Sender:
            async def send_and_wait(self, *args, **kwargs):
                await asyncio.sleep(1)

        async def test():
            rpc = KafkaRPC("offline-test")
            rpc.producer = Sender()
            result = await rpc.request(make_request("CREATE_INCIDENT", DATA), timeout=0.01)
            self.assertFalse(result["success"])
            self.assertEqual(rpc.pending, {})

        asyncio.run(test())


class APIWrapperTests(unittest.TestCase):
    def test_api_preserves_original_correlation(self):
        import httpx
        from fastapi import FastAPI

        from backend.routes_hw08 import router

        class RecordingTransport:
            async def request(self, request):
                self.received = request
                return {"correlation_id": request["correlation_id"], "success": True}

        async def test():
            app = FastAPI()
            app.include_router(router)
            app.state.hw08_rpc = RecordingTransport()
            request = make_request("CREATE_INCIDENT", DATA, correlation_id=" caller-owned-2562 ")
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/api/hw08/incidents", json=request)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(app.state.hw08_rpc.received, request)
            self.assertEqual(response.json()["correlation_id"], request["correlation_id"])

        asyncio.run(test())

    def test_disabled_transport_returns_503(self):
        import httpx
        from fastapi import FastAPI

        from backend.routes_hw08 import router

        async def test():
            app = FastAPI()
            app.include_router(router)
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/api/hw08/incidents", json=make_request("CREATE_INCIDENT", DATA))
                invalid = await client.post("/api/hw08/incidents", json={"operation": "CREATE_INCIDENT"})
            self.assertEqual(response.status_code, 503)
            self.assertEqual(invalid.status_code, 422)

        asyncio.run(test())


def run_tests():
    suite = unittest.defaultTestLoader.loadTestsFromModule(__import__(__name__, fromlist=["x"]))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(
        f"Priyank Mehta - {result.testsRun - len(result.failures) - len(result.errors)}/{result.testsRun} offline tests passed"
    )
    return result.wasSuccessful()


if __name__ == "__main__":
    raise SystemExit(0 if run_tests() else 1)
