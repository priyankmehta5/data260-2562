from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from . import crud, schemas
from .database import get_db


router = APIRouter(prefix="/api")


# ---------- Transit agencies ----------

@router.post(
    "/agencies",
    response_model=schemas.AgencyResponse,
    status_code=201,
)
def create_agency(
    data: schemas.AgencyCreate,
    database: Session = Depends(get_db),
):
    return crud.create_agency(database, data)


@router.get(
    "/agencies",
    response_model=list[schemas.AgencyResponse],
)
def list_agencies(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    database: Session = Depends(get_db),
):
    return crud.list_agencies(
        database,
        skip,
        limit,
    )


@router.get(
    "/agencies/{agency_id}",
    response_model=schemas.AgencyResponse,
)
def get_agency(
    agency_id: int,
    database: Session = Depends(get_db),
):
    return crud.get_agency(database, agency_id)


@router.put(
    "/agencies/{agency_id}",
    response_model=schemas.AgencyResponse,
)
def update_agency(
    agency_id: int,
    data: schemas.AgencyUpdate,
    database: Session = Depends(get_db),
):
    return crud.update_agency(
        database,
        agency_id,
        data,
    )


@router.delete(
    "/agencies/{agency_id}",
    status_code=204,
)
def delete_agency(
    agency_id: int,
    database: Session = Depends(get_db),
):
    crud.delete_agency(database, agency_id)
    return Response(status_code=204)


@router.get(
    "/agencies/{agency_id}/incidents",
    response_model=list[schemas.IncidentResponse],
)
def get_agency_incidents(
    agency_id: int,
    database: Session = Depends(get_db),
):
    return crud.incidents_by_agency(
        database,
        agency_id,
    )


# ---------- Transit incidents ----------

@router.post(
    "/incidents",
    response_model=schemas.IncidentResponse,
    status_code=201,
)
def create_incident(
    data: schemas.IncidentCreate,
    database: Session = Depends(get_db),
):
    return crud.create_incident(database, data)


@router.get(
    "/incidents",
    response_model=list[schemas.IncidentResponse],
)
def list_incidents(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    database: Session = Depends(get_db),
):
    return crud.list_incidents(
        database,
        skip,
        limit,
    )


@router.get(
    "/incidents/{incident_id}",
    response_model=schemas.IncidentResponse,
)
def get_incident(
    incident_id: int,
    database: Session = Depends(get_db),
):
    return crud.get_incident(
        database,
        incident_id,
    )


@router.put(
    "/incidents/{incident_id}",
    response_model=schemas.IncidentResponse,
)
def update_incident(
    incident_id: int,
    data: schemas.IncidentUpdate,
    database: Session = Depends(get_db),
):
    return crud.update_incident(
        database,
        incident_id,
        data,
    )


@router.delete(
    "/incidents/{incident_id}",
    status_code=204,
)
def delete_incident(
    incident_id: int,
    database: Session = Depends(get_db),
):
    crud.delete_incident(database, incident_id)
    return Response(status_code=204)