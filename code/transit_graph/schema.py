from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, field_validator


Tag = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=3,
        max_length=30
    )
]


class PlannerOutput(BaseModel):
    tags: list[Tag] = Field(
        min_length=3,
        max_length=3
    )
    summary: str

    @field_validator("summary")
    @classmethod
    def validate_summary(cls, value: str) -> str:
        summary = " ".join(value.split())

        if not summary:
            raise ValueError("summary cannot be empty")

        if len(summary.split()) > 25:
            raise ValueError(
                "summary must contain no more than 25 words"
            )

        return summary