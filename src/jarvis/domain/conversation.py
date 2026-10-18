from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

from jarvis.domain.configuration import BuildValidationResult, VehicleBuild
from jarvis.domain.knowledge import SourceType


class QueryIntent(StrEnum):
    GREETING = "greeting"
    COMPARISON = "comparison"
    PRICING = "pricing"
    TECHNICAL_SPECIFICATION = "technical_specification"
    INVENTORY_SEARCH = "inventory_search"
    WARRANTY_AND_SAFETY = "warranty_and_safety"
    CONFIGURATION = "configuration"


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class VehicleComparison(BaseModel):
    first_vehicle: str
    second_vehicle: str
    efficiency_winner: str
    power_winner: str
    summary: str


class LanguageModelReply(BaseModel):
    reply: str
    active_build: VehicleBuild = Field(default_factory=VehicleBuild)
    comparison: VehicleComparison | None = None
    cited_source_ids: list[str] = Field(default_factory=list)


class AssistantRequest(BaseModel):
    question: str
    history: list[ChatTurn] = Field(default_factory=list)
    current_build: VehicleBuild = Field(default_factory=VehicleBuild)
    session_id: str | None = None


class SourceReference(BaseModel):
    document_id: str
    title: str
    source_type: SourceType
    relevance_score: float
    was_cited: bool


class AssistantResponse(BaseModel):
    reply: str
    intent: QueryIntent
    active_build: VehicleBuild
    validation: BuildValidationResult
    comparison: VehicleComparison | None = None
    sources: list[SourceReference] = Field(default_factory=list)
    trace_id: str
    latency_ms: float
