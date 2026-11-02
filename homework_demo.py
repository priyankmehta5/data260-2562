"""Part 1: client-owned correlation IDs, CREATE_INCIDENT then GET_INCIDENT over Kafka."""

import argparse
import asyncio
import json
from uuid import uuid4

import httpx

from backend.hw08_common import RAW, emit
from backend.hw08_rpc import KafkaRPC, make_request


async def demonstrate(via_api=True):
    values = {
        "title": "Route 2 signal delay",
        "description": "Signal fault reported to transit operations",
        "incident_code": "HW8-" + uuid4().hex[:12].upper(),
        "severity": 3,
        "agency_id": 1,
    }
    rpc = None
    if not via_api:
        rpc = KafkaRPC("demo")
        await rpc.start()
    async with httpx.AsyncClient(timeout=25) as client:

        async def call(request):
            emit("demo", "http_request" if via_api else "kafka_request", message=request)
            if rpc:
                response = await rpc.request(request)
            else:
                result = await client.post("http://127.0.0.1:8762/api/hw08/incidents", json=request)
                result.raise_for_status()
                response = result.json()
            assert response["correlation_id"] == request["correlation_id"], "Correlation changed in transit"
            emit("demo", "response", message=response)
            return response

        try:
            create = make_request("CREATE_INCIDENT", values)  # Generated once here; API and worker preserve it.
            created = await call(create)
            assert created["success"], created
            get = make_request("GET_INCIDENT", {"incident_id": created["incident_id"]})
            retrieved = await call(get)
            assert retrieved["success"] and retrieved["incident"] == {"incident_id": created["incident_id"], **values}
            output = {
                "create_request": create,
                "create_response": created,
                "get_request": get,
                "get_response": retrieved,
                "correlation_preserved": True,
                "via_api": via_api,
            }
            RAW.mkdir(parents=True, exist_ok=True)
            (RAW / "rpc_demo.json").write_text(json.dumps(output, indent=2), encoding="utf-8")
            print("Priyank Mehta - PASS CREATE_INCIDENT -> GET_INCIDENT; both correlation IDs preserved", flush=True)
            return output
        finally:
            if rpc:
                await rpc.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--direct-kafka", action="store_true")
    args = parser.parse_args()
    asyncio.run(demonstrate(not args.direct_kafka))
