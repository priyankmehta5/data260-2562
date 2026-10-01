import secrets
from datetime import datetime, timedelta
import time

import bcrypt
from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Request,
    Response,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session as DatabaseSession

from .database import Base, engine, get_db
from .models import Incident, IncidentNote, Session, User
from .schemas import (
    IncidentCreate,
    IncidentResponse,
    IncidentUpdate,
    LoginRequest,
    UserResponse,
)


Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Municipal Transit Incident API",
    version="4.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_current_user(
    request: Request,
    database: DatabaseSession = Depends(get_db),
):
    token = request.cookies.get("session_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login required",
        )

    stored_session = (
        database.query(Session)
        .filter(
            Session.token == token,
            Session.expires_at > datetime.utcnow(),
        )
        .first()
    )

    if stored_session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )

    user = database.get(User, stored_session.user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


@app.get("/")
def root():
    return {"message": "HW4 API is running"}


@app.post("/api/login", response_model=UserResponse)
def login(
    credentials: LoginRequest,
    response: Response,
    database: DatabaseSession = Depends(get_db),
):
    user = (
        database.query(User)
        .filter(User.email == credentials.email.strip().lower())
        .first()
    )

    password_valid = (
        user is not None
        and bcrypt.checkpw(
            credentials.password.encode("utf-8"),
            user.password_hash.encode("utf-8"),
        )
    )

    if not password_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = secrets.token_urlsafe(48)
    expires_at = datetime.utcnow() + timedelta(hours=8)

    database.add(
        Session(
            token=token,
            user_id=user.id,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
        )
    )
    database.commit()

    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=8 * 60 * 60,
    )

    return user


@app.post("/api/logout", status_code=204)
def logout(
    request: Request,
    response: Response,
    database: DatabaseSession = Depends(get_db),
):
    token = request.cookies.get("session_token")

    if token:
        database.query(Session).filter(
            Session.token == token
        ).delete()
        database.commit()

    response.delete_cookie("session_token")
    return Response(status_code=204)


@app.get("/api/session", response_model=UserResponse)
def session_status(
    user: User = Depends(get_current_user),
):
    return user


@app.get("/api/incidents", response_model=list[IncidentResponse])
def get_incidents(
    database: DatabaseSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return database.query(Incident).order_by(Incident.id).all()


@app.get(
    "/api/incidents/{incident_id}",
    response_model=IncidentResponse,
)
def get_incident(
    incident_id: int,
    database: DatabaseSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    incident = database.get(Incident, incident_id)

    if incident is None:
        raise HTTPException(404, "Incident not found")

    return incident


@app.post(
    "/api/incidents",
    response_model=IncidentResponse,
    status_code=201,
)
def create_incident(
    data: IncidentCreate,
    database: DatabaseSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    incident = Incident(
        title=data.title.strip(),
        description=data.description.strip(),
    )

    database.add(incident)
    database.commit()
    database.refresh(incident)
    return incident


@app.put(
    "/api/incidents/{incident_id}",
    response_model=IncidentResponse,
)
def update_incident(
    incident_id: int,
    data: IncidentUpdate,
    database: DatabaseSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    incident = database.get(Incident, incident_id)

    if incident is None:
        raise HTTPException(404, "Incident not found")

    incident.title = data.title.strip()
    incident.description = data.description.strip()

    database.commit()
    database.refresh(incident)
    return incident


@app.delete(
    "/api/incidents/{incident_id}",
    status_code=204,
)
def delete_incident(
    incident_id: int,
    database: DatabaseSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    incident = database.get(Incident, incident_id)

    if incident is None:
        raise HTTPException(404, "Incident not found")

    database.delete(incident)
    database.commit()
    return Response(status_code=204)

@app.get("/api/performance/incidents-naive")
def get_incidents_naive(
    response: Response,
    page_size: int = 10,
    database: DatabaseSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if page_size not in {10, 50, 200}:
        raise HTTPException(
            status_code=400,
            detail="page_size must be 10, 50, or 200",
        )

    started = time.perf_counter()

    incidents = (
        database.query(Incident)
        .order_by(Incident.id)
        .limit(page_size)
        .all()
    )

    records = []

    for incident in incidents:
        notes = (
            database.query(IncidentNote)
            .filter(IncidentNote.incident_id == incident.id)
            .all()
        )

        records.append(
            {
                "id": incident.id,
                "title": incident.title,
                "description": incident.description,
                "notes": [
                    {
                        "id": note.id,
                        "note": note.note,
                    }
                    for note in notes
                ],
            }
        )

    latency_ms = round(
        (time.perf_counter() - started) * 1000,
        3,
    )
    sql_queries = 1 + len(incidents)

    response.headers["X-SQL-Queries"] = str(sql_queries)
    response.headers["X-Retrieval-Latency-MS"] = str(
        latency_ms
    )

    return {
        "version": "naive",
        "page_size": page_size,
        "sql_queries": sql_queries,
        "retrieval_latency_ms": latency_ms,
        "records": records,
    }


@app.get("/api/performance/incidents-optimized")
def get_incidents_optimized(
    response: Response,
    page_size: int = 10,
    database: DatabaseSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if page_size not in {10, 50, 200}:
        raise HTTPException(
            status_code=400,
            detail="page_size must be 10, 50, or 200",
        )

    started = time.perf_counter()

    incident_page = (
        database.query(Incident.id)
        .order_by(Incident.id)
        .limit(page_size)
        .subquery()
    )

    rows = (
        database.query(Incident, IncidentNote)
        .join(
            incident_page,
            Incident.id == incident_page.c.id,
        )
        .outerjoin(
            IncidentNote,
            Incident.id == IncidentNote.incident_id,
        )
        .order_by(Incident.id)
        .all()
    )

    records_by_id = {}

    for incident, note in rows:
        if incident.id not in records_by_id:
            records_by_id[incident.id] = {
                "id": incident.id,
                "title": incident.title,
                "description": incident.description,
                "notes": [],
            }

        if note is not None:
            records_by_id[incident.id]["notes"].append(
                {
                    "id": note.id,
                    "note": note.note,
                }
            )

    records = list(records_by_id.values())

    latency_ms = round(
        (time.perf_counter() - started) * 1000,
        3,
    )
    sql_queries = 1

    response.headers["X-SQL-Queries"] = str(sql_queries)
    response.headers["X-Retrieval-Latency-MS"] = str(
        latency_ms
    )

    return {
        "version": "optimized",
        "page_size": page_size,
        "sql_queries": sql_queries,
        "retrieval_latency_ms": latency_ms,
        "records": records,
    }