from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: int
    name: str
    email: str

    model_config = ConfigDict(from_attributes=True)


class IncidentCreate(BaseModel):
    title: str = Field(min_length=3, max_length=100)
    description: str = Field(min_length=3, max_length=1000)


class IncidentUpdate(IncidentCreate):
    pass


class IncidentResponse(IncidentCreate):
    id: int

    model_config = ConfigDict(from_attributes=True)