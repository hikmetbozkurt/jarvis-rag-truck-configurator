from pydantic import BaseModel, Field

from jarvis.domain.configuration import VehicleBuild
from jarvis.domain.conversation import ChatTurn


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=50)
    active_build: VehicleBuild = Field(default_factory=VehicleBuild)
    session_id: str | None = Field(default=None, max_length=100)


class HealthResponse(BaseModel):
    status: str


class ReadinessResponse(BaseModel):
    status: str
    indexed_document_count: int
    language_model_provider: str
    language_model_name: str
    language_model_reachable: bool


class ErrorResponse(BaseModel):
    detail: str
