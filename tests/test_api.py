from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from jarvis.api.app import create_app
from jarvis.bootstrap import ApplicationContainer
from jarvis.config import Settings
from jarvis.generation.prompt_builder import PromptBuilder
from jarvis.observability.tracing import InMemoryTraceStore
from jarvis.retrieval.hybrid_retriever import HybridRetriever
from jarvis.retrieval.query_analysis import KeywordIntentClassifier
from jarvis.retrieval.vector_store import ChromaVectorStore
from jarvis.rules.catalog_vocabulary import CatalogVocabulary
from jarvis.rules.configuration_validator import ConfigurationValidator
from jarvis.services.configuration_assistant import ConfigurationAssistant
from tests.fakes import ScriptedChatClient, UnavailableChatClient


def build_test_client(
    chat_client: ScriptedChatClient,
    populated_vector_store: ChromaVectorStore,
    hybrid_retriever: HybridRetriever,
    catalog_vocabulary: CatalogVocabulary,
    configuration_validator: ConfigurationValidator,
) -> TestClient:
    def build_container(settings: Settings) -> ApplicationContainer:
        trace_store = InMemoryTraceStore(capacity=10)
        assistant = ConfigurationAssistant(
            intent_classifier=KeywordIntentClassifier(),
            retriever=hybrid_retriever,
            prompt_builder=PromptBuilder(catalog_vocabulary, history_turn_limit=4),
            chat_client=chat_client,
            catalog_vocabulary=catalog_vocabulary,
            configuration_validator=configuration_validator,
            trace_sink=trace_store,
        )
        return ApplicationContainer(
            settings=settings,
            vector_store=populated_vector_store,
            retriever=hybrid_retriever,
            chat_client=chat_client,
            assistant=assistant,
            trace_store=trace_store,
        )

    return TestClient(create_app(Settings(), container_factory=build_container))


@pytest.fixture
def api_client(
    populated_vector_store: ChromaVectorStore,
    hybrid_retriever: HybridRetriever,
    catalog_vocabulary: CatalogVocabulary,
    configuration_validator: ConfigurationValidator,
) -> Iterator[TestClient]:
    chat_client = ScriptedChatClient(
        {
            "reply": "The F-350 starts at $49,500.",
            "active_build": {"model": "Ford F-350"},
            "comparison": None,
            "cited_source_ids": ["PRICE-M2"],
        }
    )
    with build_test_client(
        chat_client, populated_vector_store, hybrid_retriever, catalog_vocabulary, configuration_validator
    ) as client:
        yield client


def test_health_and_readiness(api_client: TestClient) -> None:
    assert api_client.get("/api/v1/health").json() == {"status": "ok"}

    readiness = api_client.get("/api/v1/ready").json()
    assert readiness["status"] == "ready"
    assert readiness["indexed_document_count"] > 200


def test_chat_returns_sources_and_a_retrievable_trace(api_client: TestClient) -> None:
    response = api_client.post("/api/v1/chat", json={"message": "How much does the Ford F-350 cost?"})

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "pricing"
    assert body["active_build"]["model"] == "Ford F-350"
    assert body["validation"]["status"] == "incomplete"
    assert body["sources"]
    assert response.headers["X-Request-ID"]

    trace = api_client.get(f"/api/v1/traces/{body['trace_id']}").json()
    assert trace["question"] == "How much does the Ford F-350 cost?"
    assert "vector" in trace["candidates_by_channel"]


def test_chat_rejects_empty_message(api_client: TestClient) -> None:
    assert api_client.post("/api/v1/chat", json={"message": ""}).status_code == 422


def test_unknown_trace_returns_404(api_client: TestClient) -> None:
    assert api_client.get("/api/v1/traces/does-not-exist").status_code == 404


def test_language_model_outage_returns_503(
    populated_vector_store: ChromaVectorStore,
    hybrid_retriever: HybridRetriever,
    catalog_vocabulary: CatalogVocabulary,
    configuration_validator: ConfigurationValidator,
) -> None:
    with build_test_client(
        UnavailableChatClient(),
        populated_vector_store,
        hybrid_retriever,
        catalog_vocabulary,
        configuration_validator,
    ) as client:
        response = client.post("/api/v1/chat", json={"message": "What does the RAM 2500 cost?"})
        readiness = client.get("/api/v1/ready").json()

    assert response.status_code == 503
    assert readiness["status"] == "degraded"
