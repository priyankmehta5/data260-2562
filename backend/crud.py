from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import models, schemas


def commit_or_conflict(
    database: Session,
    message: str,
):
    try:
        database.commit()
    except IntegrityError as error:
        database.rollback()
        raise HTTPException(
            status_code=409,
            detail=message,
        ) from error


# ---------- Transit agencies ----------

def create_agency(
    database: Session,
    data: schemas.AgencyCreate,
):
    agency = models.TransitAgency(**data.model_dump())
    database.add(agency)

    commit_or_conflict(
        database,
        "Agency code must be unique",
    )

    database.refresh(agency)
    return agency


def list_agencies(
    database: Session,
    skip: int,
    limit: int,
):
    return database.scalars(
        select(models.TransitAgency)
        .order_by(models.TransitAgency.id)
        .offset(skip)
        .limit(limit)
    ).all()


def get_agency(
    database: Session,
    agency_id: int,
):
    agency = database.get(
        models.TransitAgency,
        agency_id,
    )

    if agency is None:
        raise HTTPException(
            status_code=404,
            detail="Transit agency not found",
        )

    return agency


def update_agency(
    database: Session,
    agency_id: int,
    data: schemas.AgencyUpdate,
):
    agency = get_agency(database, agency_id)

    for field, value in data.model_dump(
        exclude_unset=True
    ).items():
        setattr(agency, field, value)

    commit_or_conflict(
        database,
        "Agency code must be unique",
    )

    database.refresh(agency)
    return agency


def delete_agency(
    database: Session,
    agency_id: int,
):
    agency = get_agency(database, agency_id)

    incident_count = database.scalar(
        select(func.count(models.Incident.id)).where(
            models.Incident.agency_id == agency_id
        )
    )

    if incident_count:
        raise HTTPException(
            status_code=409,
            detail=(
                "Cannot delete an agency that has "
                "associated incidents"
            ),
        )

    database.delete(agency)
    database.commit()


# ---------- Incidents ----------

def create_incident(
    database: Session,
    data: schemas.IncidentCreate,
):
    get_agency(database, data.agency_id)

    incident = models.Incident(**data.model_dump())
    database.add(incident)

    commit_or_conflict(
        database,
        "Incident code must be unique",
    )

    database.refresh(incident)
    return incident


def list_incidents(
    database: Session,
    skip: int,
    limit: int,
):
    return database.scalars(
        select(models.Incident)
        .order_by(models.Incident.id)
        .offset(skip)
        .limit(limit)
    ).all()


def get_incident(
    database: Session,
    incident_id: int,
):
    incident = database.get(
        models.Incident,
        incident_id,
    )

    if incident is None:
        raise HTTPException(
            status_code=404,
            detail="Incident not found",
        )

    return incident


def update_incident(
    database: Session,
    incident_id: int,
    data: schemas.IncidentUpdate,
):
    incident = get_incident(database, incident_id)
    changes = data.model_dump(exclude_unset=True)

    if "agency_id" in changes:
        get_agency(database, changes["agency_id"])

    for field, value in changes.items():
        setattr(incident, field, value)

    commit_or_conflict(
        database,
        "Incident code must be unique",
    )

    database.refresh(incident)
    return incident


def delete_incident(
    database: Session,
    incident_id: int,
):
    incident = get_incident(database, incident_id)
    database.delete(incident)
    database.commit()


def incidents_by_agency(
    database: Session,
    agency_id: int,
):
    get_agency(database, agency_id)

    return database.scalars(
        select(models.Incident)
        .where(models.Incident.agency_id == agency_id)
        .order_by(models.Incident.id)
    ).all()