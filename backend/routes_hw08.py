"""HW8 Kafka-only API wrapper; shares the existing FastAPI application."""

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

router = APIRouter(prefix="/api/hw08", tags=["HW8 Kafka incident service"])


class IncidentOperation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    correlation_id: str = Field(min_length=1, max_length=100)
    reply_to: str
    operation: str
    data: dict[str, Any]


@router.post("/incidents")
async def incident_operation(payload: IncidentOperation, request: Request):
    rpc = getattr(request.app.state, "hw08_rpc", None)
    if rpc is None:
        raise HTTPException(503, "Start this application with HW08_KAFKA_ENABLED=1")
    return await rpc.request(payload.model_dump())


@router.get("/health")
async def kafka_health(request: Request):
    return {
        "homework": "8",
        "enabled": getattr(request.app.state, "hw08_rpc", None) is not None,
        "request_topic": "s2562_entity_requests",
        "response_topic": "s2562_entity_responses",
    }
