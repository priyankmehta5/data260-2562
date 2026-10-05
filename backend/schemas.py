from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


CODE_PATTERN = r"^[A-Z][A-Z0-9-]{2,29}$"


class LoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: int
    name: str
    email: str

    model_config = ConfigDict(from_attributes=True)


class AgencyCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    jurisdiction: str = Field(min_length=2, max_length=150)
    agency_code: str = Field(
        min_length=3,
        max_length=30,
        pattern=CODE_PATTERN,
    )

    @field_validator("name", "jurisdiction")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("agency_code", mode="before")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return str(value).strip().upper()


class AgencyUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
    )
    jurisdiction: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
    )
    agency_code: str | None = Field(
        default=None,
        min_length=3,
        max_length=30,
        pattern=CODE_PATTERN,
    )

    @field_validator("name", "jurisdiction")
    @classmethod
    def strip_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("agency_code", mode="before")
    @classmethod
    def normalize_optional_code(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None
        return str(value).strip().upper()


class AgencyResponse(AgencyCreate):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IncidentCreate(BaseModel):
    title: str = Field(min_length=3, max_length=100)
    description: str = Field(min_length=3, max_length=1000)
    incident_code: str = Field(
        min_length=3,
        max_length=30,
        pattern=CODE_PATTERN,
    )
    severity: int = Field(default=1, ge=1, le=5)
    agency_id: int = Field(gt=0)

    @field_validator("title", "description")
    @classmethod
    def strip_incident_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("incident_code", mode="before")
    @classmethod
    def normalize_incident_code(cls, value: str) -> str:
        return str(value).strip().upper()


class IncidentUpdate(BaseModel):
    title: str | None = Field(
        default=None,
        min_length=3,
        max_length=100,
    )
    description: str | None = Field(
        default=None,
        min_length=3,
        max_length=1000,
    )
    incident_code: str | None = Field(
        default=None,
        min_length=3,
        max_length=30,
        pattern=CODE_PATTERN,
    )
    severity: int | None = Field(
        default=None,
        ge=1,
        le=5,
    )
    agency_id: int | None = Field(
        default=None,
        gt=0,
    )

    @field_validator("title", "description")
    @classmethod
    def strip_optional_incident_text(
        cls,
        value: str | None,
    ) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("incident_code", mode="before")
    @classmethod
    def normalize_optional_incident_code(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None
        return str(value).strip().upper()


class IncidentResponse(BaseModel):
    id: int
    title: str
    description: str
    incident_code: str
    severity: int
    agency_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)