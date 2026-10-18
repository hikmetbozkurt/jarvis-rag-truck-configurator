from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class LanguageModelProvider(StrEnum):
    OLLAMA = "ollama"
    OPENAI_COMPATIBLE = "openai_compatible"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="JARVIS_", env_file=".env", extra="ignore")

    data_directory: Path = PROJECT_ROOT / "data"
    vector_store_directory: Path = PROJECT_ROOT / "storage" / "vector_store"
    collection_name: str = "truck-knowledge-base"
    auto_ingest_on_startup: bool = False

    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    reranker_model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    reranker_enabled: bool = True

    llm_provider: LanguageModelProvider = LanguageModelProvider.OLLAMA
    llm_model_name: str = "mistral"
    llm_base_url: str = "http://localhost:11434"
    llm_api_key: str | None = None
    llm_temperature: float = 0.2
    llm_context_window_tokens: int = 8192
    llm_request_timeout_seconds: float = 120.0

    retrieval_candidate_count: int = Field(default=20, ge=1)
    rerank_candidate_count: int = Field(default=20, ge=1)
    context_document_count: int = Field(default=5, ge=1)
    rrf_rank_constant: int = Field(default=60, ge=1)
    conversation_history_turn_limit: int = Field(default=8, ge=0)

    cors_allowed_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    log_level: str = "INFO"
    log_as_json: bool = False

    trace_log_path: Path = PROJECT_ROOT / "storage" / "traces" / "request_traces.jsonl"
    trace_memory_capacity: int = 200
    langfuse_enabled: bool = False

    golden_set_path: Path = PROJECT_ROOT / "evaluation" / "golden_set.json"
    evaluation_report_directory: Path = PROJECT_ROOT / "evaluation" / "reports"


@lru_cache
def get_settings() -> Settings:
    return Settings()
