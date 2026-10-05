from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class TransitAgency(Base):
    __tablename__ = "transit_agencies"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    jurisdiction: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    agency_code: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    incidents: Mapped[list["Incident"]] = relationship(
        back_populates="agency",
        passive_deletes=True,
    )


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    title: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    incident_code: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        nullable=False,
        index=True,
    )
    severity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
    agency_id: Mapped[int] = mapped_column(
        ForeignKey(
            "transit_agencies.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    agency: Mapped["TransitAgency"] = relationship(
        back_populates="incidents",
    )


class IncidentNote(Base):
    __tablename__ = "incident_notes"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    incident_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    note: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    token: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )