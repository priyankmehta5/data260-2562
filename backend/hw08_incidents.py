"""Validated dictionary-backed incident operations used only by the Kafka worker."""

from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, StrictInt, ValidationError, field_validator

from .hw08_common import RESPONSES, fingerprint


class KafkaIncidentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: str = Field(min_length=3, max_length=100)
    description: str = Field(min_length=3, max_length=1000)
    incident_code: str = Field(pattern=r"^[A-Z][A-Z0-9-]{2,29}$")
    severity: StrictInt = Field(ge=1, le=5)
    agency_id: StrictInt = Field(gt=0)

    @field_validator("incident_code", mode="before")
    @classmethod
    def normalize_code(cls, value):
        return value.strip().upper() if isinstance(value, str) else value


class IncidentService:
    def __init__(self, idempotent=True):
        self.incidents = {}  # Assignment requires plain Python dictionary storage.
        self.responses = {}
        self.idempotent = idempotent

    def process(self, request):
        cid = request.get("correlation_id") if isinstance(request, dict) else None

        def error(message):
            return {"correlation_id": cid, "success": False, "error": message}

        if not isinstance(cid, str) or not cid.strip():
            return error("correlation_id is required")
        if request.get("reply_to") != RESPONSES:
            return error(f"reply_to must be {RESPONSES}")
        operation, data = request.get("operation"), request.get("data")
        signature = fingerprint({"operation": operation, "data": data})
        if self.idempotent and cid in self.responses:
            previous, response = self.responses[cid]
            return dict(response) if previous == signature else error("correlation_id reused with different input")
        if not isinstance(data, dict):
            return error("data must be an object")
        if operation == "CREATE_INCIDENT":
            try:
                values = KafkaIncidentCreate.model_validate(data).model_dump()
            except ValidationError as exc:
                return error(
                    "Invalid incident: "
                    + "; ".join(f"{'.'.join(map(str, x['loc']))}: {x['msg']}" for x in exc.errors())
                )
            identifier = str(uuid4())
            self.incidents[identifier] = {"incident_id": identifier, **values}
            response = {
                "correlation_id": cid,
                "success": True,
                "incident_id": identifier,
                "message": "Incident created",
            }
        elif operation == "GET_INCIDENT":
            if set(data) != {"incident_id"}:
                return error("GET_INCIDENT requires only incident_id")
            try:
                identifier = str(UUID(data["incident_id"]))
            except (ValueError, TypeError, AttributeError):
                return error("incident_id must be a UUID")
            if identifier not in self.incidents:
                return error("Incident not found")
            response = {"correlation_id": cid, "success": True, "incident": dict(self.incidents[identifier])}
        else:
            return error("Unknown operation")
        if self.idempotent:
            self.responses[cid] = signature, response
        return response
