"""Pydantic schemas and enums for the HW6 MongoDB document and chat APIs."""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DocumentStatus(str, Enum):
    open = "open"
    in_progress = "in_progress"
    done = "done"


class DocumentCategory(str, Enum):
    service = "service"
    safety = "safety"
    operations = "operations"
    other = "other"


class DocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    description: str | None = None
    status: DocumentStatus = DocumentStatus.open
    category: DocumentCategory = DocumentCategory.other
    due_at: datetime

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("title must not be blank")
        return value


class DocumentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    status: DocumentStatus | None = None
    category: DocumentCategory | None = None
    due_at: datetime | None = None


class DocumentResponse(DocumentCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime
    updated_at: datetime


class ChatRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=100)
    session_id: str | None = Field(default=None, max_length=100)
    message: str = Field(min_length=1, max_length=4000)
