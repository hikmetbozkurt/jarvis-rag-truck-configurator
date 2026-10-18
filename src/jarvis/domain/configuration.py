from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

BuildField = Literal["model", "engine", "transmission", "trim", "application", "region"]
REQUIRED_BUILD_FIELDS: tuple[BuildField, ...] = ("model", "engine", "transmission", "trim")


class VehicleBuild(BaseModel):
    model: str | None = None
    engine: str | None = None
    transmission: str | None = None
    trim: str | None = None
    application: str | None = None
    region: str | None = None

    def read_field(self, field_name: str) -> str | None:
        value = getattr(self, field_name, None)
        return value if isinstance(value, str) and value.strip() else None

    def merge_with(self, newer_build: "VehicleBuild") -> "VehicleBuild":
        merged_values = self.model_dump()
        for field_name, value in newer_build.model_dump().items():
            if isinstance(value, str) and value.strip():
                merged_values[field_name] = value.strip()
        return VehicleBuild(**merged_values)


class BuildStatus(StrEnum):
    INCOMPLETE = "incomplete"
    VALID = "valid"
    INVALID = "invalid"


class RuleType(StrEnum):
    CONSTRAINT = "constraint"
    RECOMMENDATION = "recommendation"


class CompatibilityRule(BaseModel):
    rule_id: str = Field(alias="id")
    rule_type: RuleType = Field(alias="type")
    conditions: dict[str, str]
    forbidden: dict[str, str] = Field(default_factory=dict)
    required: dict[str, str] = Field(default_factory=dict)
    recommendation: str | None = None
    message: str

    model_config = {"populate_by_name": True}


class RuleFinding(BaseModel):
    rule_id: str
    rule_type: RuleType
    message: str


class BuildValidationResult(BaseModel):
    status: BuildStatus
    missing_fields: list[str] = Field(default_factory=list)
    violations: list[RuleFinding] = Field(default_factory=list)
    recommendations: list[RuleFinding] = Field(default_factory=list)
