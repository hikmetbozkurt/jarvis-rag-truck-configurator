import logging
import threading
import uuid
from collections import OrderedDict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel, Field

from jarvis.domain.conversation import QueryIntent
from jarvis.domain.knowledge import ScoredDocument

logger = logging.getLogger(__name__)

_FUSED_CANDIDATES_KEPT_IN_TRACE = 15


class DocumentHit(BaseModel):
    document_id: str
    source_type: str
    score: float
    rank: int

    @classmethod
    def from_scored_document(cls, scored_document: ScoredDocument) -> "DocumentHit":
        return cls(
            document_id=scored_document.document.document_id,
            source_type=scored_document.document.source_type.value,
            score=scored_document.score,
            rank=scored_document.rank,
        )


class LanguageModelCallTrace(BaseModel):
    provider: str
    model_name: str
    prompt_character_count: int
    estimated_prompt_tokens: int
    output_character_count: int = 0
    reply_parsed: bool = False
    parse_error: str | None = None


class RequestTrace(BaseModel):
    trace_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    session_id: str | None = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    question: str
    intent: QueryIntent | None = None
    applied_filters: dict[str, Any] = Field(default_factory=dict)
    candidates_by_channel: dict[str, list[DocumentHit]] = Field(default_factory=dict)
    fused_candidates: list[DocumentHit] = Field(default_factory=list)
    context_documents: list[DocumentHit] = Field(default_factory=list)
    cited_source_ids: list[str] = Field(default_factory=list)
    unknown_citation_ids: list[str] = Field(default_factory=list)
    language_model: LanguageModelCallTrace | None = None
    validation_status: str | None = None
    violated_rule_ids: list[str] = Field(default_factory=list)
    stage_durations_ms: dict[str, float] = Field(default_factory=dict)
    total_duration_ms: float = 0.0
    error: str | None = None

    def record_retrieval_candidates(
        self,
        candidates_by_channel: dict[str, list[ScoredDocument]],
        fused_candidates: list[ScoredDocument],
        context_documents: list[ScoredDocument],
    ) -> None:
        self.candidates_by_channel = {
            channel_name: [DocumentHit.from_scored_document(candidate) for candidate in candidates]
            for channel_name, candidates in candidates_by_channel.items()
        }
        self.fused_candidates = [
            DocumentHit.from_scored_document(candidate)
            for candidate in fused_candidates[:_FUSED_CANDIDATES_KEPT_IN_TRACE]
        ]
        self.context_documents = [
            DocumentHit.from_scored_document(document) for document in context_documents
        ]


class TraceSink(Protocol):
    def record_trace(self, trace: RequestTrace) -> None: ...


class JsonlTraceSink:
    def __init__(self, trace_file_path: Path) -> None:
        self._trace_file_path = trace_file_path
        self._write_lock = threading.Lock()
        trace_file_path.parent.mkdir(parents=True, exist_ok=True)

    def record_trace(self, trace: RequestTrace) -> None:
        with self._write_lock, self._trace_file_path.open("a", encoding="utf-8") as trace_file:
            trace_file.write(trace.model_dump_json() + "\n")


class InMemoryTraceStore:
    def __init__(self, capacity: int) -> None:
        self._capacity = capacity
        self._traces_by_id: OrderedDict[str, RequestTrace] = OrderedDict()
        self._lock = threading.Lock()

    def record_trace(self, trace: RequestTrace) -> None:
        with self._lock:
            self._traces_by_id[trace.trace_id] = trace
            while len(self._traces_by_id) > self._capacity:
                self._traces_by_id.popitem(last=False)

    def find_trace(self, trace_id: str) -> RequestTrace | None:
        with self._lock:
            return self._traces_by_id.get(trace_id)

    def list_recent_traces(self, limit: int) -> list[RequestTrace]:
        with self._lock:
            return list(reversed(self._traces_by_id.values()))[:limit]


class CompositeTraceSink:
    def __init__(self, trace_sinks: list[TraceSink]) -> None:
        self._trace_sinks = trace_sinks

    def record_trace(self, trace: RequestTrace) -> None:
        for trace_sink in self._trace_sinks:
            try:
                trace_sink.record_trace(trace)
            except Exception:
                logger.exception(
                    "Trace sink %s failed for trace %s", type(trace_sink).__name__, trace.trace_id
                )
