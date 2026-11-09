"""Authenticated HW9 ingress on the existing FastAPI application."""

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from .hw07_auth import require_roles

router = APIRouter(prefix="/api/hw09", tags=["HW9 Redis and agents"])


class Question(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    question: str = Field(min_length=3, max_length=1000)


def service(request: Request):
    instance = getattr(request.app.state, "hw09_cache", None)
    if instance is None:
        raise HTTPException(503, "Start the application with HW09_ENABLED=1")
    return instance


@router.get("/health")
def health(request: Request):
    cache = getattr(request.app.state, "hw09_cache", None)
    return {"homework": 9, "enabled": cache is not None, "threshold": cache.threshold if cache is not None else None}


@router.post("/qa", dependencies=[Depends(require_roles("reader", "writer", "moderator"))])
async def qa(body: Question, cache=Depends(service)):
    return await cache.query(body.question)


@router.post("/incidents/{incident_id}/views", dependencies=[Depends(require_roles("reader", "writer", "moderator"))])
async def views(incident_id: int, cache=Depends(service)):
    try:
        count = await asyncio.to_thread(cache.database.increment_incident_views, incident_id)
        return {"incident_id": incident_id, "views": count}
    except ValueError as error:
        raise HTTPException(404, str(error)) from error
