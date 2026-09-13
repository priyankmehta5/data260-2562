from pathlib import Path
from typing import List

import uvicorn
from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field


WEB_DIRECTORY = Path(__file__).resolve().parents[1] / "web_application"

app = FastAPI(
    title="Municipal Transit Incident API",
    version="2.0.0"
)


class Incident(BaseModel):
    id: int
    title: str
    description: str


class IncidentCreate(BaseModel):
    title: str = Field(min_length=3, max_length=100)
    description: str = Field(min_length=3, max_length=500)


class IncidentUpdate(BaseModel):
    title: str = Field(min_length=3, max_length=100)
    description: str = Field(min_length=3, max_length=500)


incidents: List[Incident] = [
    Incident(
        id=1,
        title="VTA Blue Line Signal Failure",
        description="A signal failure near Santa Clara station caused major delays."
    ),
    Incident(
        id=2,
        title="Bus Route 22 Delay",
        description="Heavy traffic caused delays along the morning route."
    ),
    Incident(
        id=3,
        title="Light Rail Maintenance",
        description="Scheduled maintenance affected service near downtown San Jose."
    )
]


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(WEB_DIRECTORY / "index.html")


@app.get("/styles.css", include_in_schema=False)
def styles():
    return FileResponse(
        WEB_DIRECTORY / "styles.css",
        media_type="text/css"
    )


@app.get("/script.js", include_in_schema=False)
def script():
    return FileResponse(
        WEB_DIRECTORY / "script.js",
        media_type="application/javascript"
    )


@app.get("/api/incidents", response_model=List[Incident])
def get_incidents(
    response: Response,
    search: str = Query(default="")
):
    response.headers["Cache-Control"] = "no-store"

    query = search.strip().lower()

    if not query:
        return incidents

    return [
        incident
        for incident in incidents
        if query in incident.title.lower()
        or query in incident.description.lower()
    ]


@app.get("/api/incidents/{incident_id}", response_model=Incident)
def get_incident(incident_id: int):
    incident = next(
        (
            item
            for item in incidents
            if item.id == incident_id
        ),
        None
    )

    if incident is None:
        raise HTTPException(
            status_code=404,
            detail="Incident not found"
        )

    return incident


@app.post(
    "/api/incidents",
    response_model=Incident,
    status_code=201
)
def create_incident(data: IncidentCreate):
    new_id = max(
        (incident.id for incident in incidents),
        default=0
    ) + 1

    incident = Incident(
        id=new_id,
        title=data.title.strip(),
        description=data.description.strip()
    )

    incidents.append(incident)
    return incident


@app.put(
    "/api/incidents/{incident_id}",
    response_model=Incident
)
def update_incident(
    incident_id: int,
    data: IncidentUpdate
):
    incident = next(
        (
            item
            for item in incidents
            if item.id == incident_id
        ),
        None
    )

    if incident is None:
        raise HTTPException(
            status_code=404,
            detail="Incident not found"
        )

    incident.title = data.title.strip()
    incident.description = data.description.strip()

    return incident


@app.delete(
    "/api/incidents/{incident_id}",
    status_code=204
)
def delete_incident(incident_id: int):
    incident = next(
        (
            item
            for item in incidents
            if item.id == incident_id
        ),
        None
    )

    if incident is None:
        raise HTTPException(
            status_code=404,
            detail="Incident not found"
        )

    incidents.remove(incident)
    return Response(status_code=204)


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8762
    )