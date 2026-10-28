"""HW7 JWT authentication and role-protected municipal transit routes."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from . import crud, schemas
from .database import get_db
from .hw07_auth import authenticate_user, create_access_token, require_roles

router = APIRouter()


class LoginBody(BaseModel):
    username: str
    password: str


@router.post("/auth/login")
def jwt_login(body: LoginBody, database: Session = Depends(get_db)):
    user = authenticate_user(database, body.username, body.password)
    role = getattr(user, "role", "reader") or "reader"
    return {"access_token": create_access_token(str(user.id), role), "token_type": "bearer", "role": role}


@router.get("/auth/me")
def jwt_me(user=Depends(require_roles("reader", "writer", "moderator"))):
    return {
        "id": user.id,
        "username": getattr(user, "username", None) or user.email,
        "email": user.email,
        "role": getattr(user, "role", "reader") or "reader",
    }


@router.get("/api/agencies", response_model=list[schemas.AgencyResponse])
def list_agencies_jwt(
    skip: int = 0,
    limit: int = 50,
    database: Session = Depends(get_db),
    user=Depends(require_roles("reader", "writer", "moderator")),
):
    return crud.list_agencies(database, skip, limit)


@router.get("/api/agencies/{agency_id}", response_model=schemas.AgencyResponse)
def get_agency_jwt(
    agency_id: int, database: Session = Depends(get_db), user=Depends(require_roles("reader", "writer", "moderator"))
):
    return crud.get_agency(database, agency_id)


@router.post("/api/agencies", response_model=schemas.AgencyResponse, status_code=201)
def create_agency_jwt(
    data: schemas.AgencyCreate, database: Session = Depends(get_db), user=Depends(require_roles("writer", "moderator"))
):
    return crud.create_agency(database, data)


@router.put("/api/agencies/{agency_id}", response_model=schemas.AgencyResponse)
def update_agency_jwt(
    agency_id: int,
    data: schemas.AgencyUpdate,
    database: Session = Depends(get_db),
    user=Depends(require_roles("writer", "moderator")),
):
    return crud.update_agency(database, agency_id, data)


@router.delete("/api/agencies/{agency_id}", status_code=204)
def delete_agency_jwt(agency_id: int, database: Session = Depends(get_db), user=Depends(require_roles("moderator"))):
    crud.delete_agency(database, agency_id)


@router.get("/api/agencies/{agency_id}/incidents", response_model=list[schemas.IncidentResponse])
def agency_incidents_jwt(
    agency_id: int, database: Session = Depends(get_db), user=Depends(require_roles("reader", "writer", "moderator"))
):
    return crud.incidents_by_agency(database, agency_id)


@router.get("/api/incidents", response_model=list[schemas.IncidentResponse])
def list_incidents_jwt(
    skip: int = 0,
    limit: int = 50,
    database: Session = Depends(get_db),
    user=Depends(require_roles("reader", "writer", "moderator")),
):
    return crud.list_incidents(database, skip, limit)


@router.get("/api/incidents/{incident_id}", response_model=schemas.IncidentResponse)
def get_incident_jwt(
    incident_id: int, database: Session = Depends(get_db), user=Depends(require_roles("reader", "writer", "moderator"))
):
    return crud.get_incident(database, incident_id)


@router.post("/api/incidents", response_model=schemas.IncidentResponse, status_code=201)
def create_incident_jwt(
    data: schemas.IncidentCreate,
    database: Session = Depends(get_db),
    user=Depends(require_roles("writer", "moderator")),
):
    return crud.create_incident(database, data)


@router.put("/api/incidents/{incident_id}", response_model=schemas.IncidentResponse)
def update_incident_jwt(
    incident_id: int,
    data: schemas.IncidentUpdate,
    database: Session = Depends(get_db),
    user=Depends(require_roles("writer", "moderator")),
):
    return crud.update_incident(database, incident_id, data)


@router.delete("/api/incidents/{incident_id}", status_code=204)
def delete_incident_jwt(
    incident_id: int, database: Session = Depends(get_db), user=Depends(require_roles("moderator"))
):
    crud.delete_incident(database, incident_id)
