from typing import Any

import pytest

from jarvis.domain.configuration import BuildStatus, VehicleBuild
from jarvis.domain.conversation import AssistantRequest, QueryIntent
from jarvis.generation.llm_clients import LanguageModelUnavailableError
from jarvis.generation.prompt_builder import PromptBuilder
from jarvis.observability.tracing import InMemoryTraceStore
from jarvis.retrieval.hybrid_retriever import HybridRetriever
from jarvis.retrieval.query_analysis import KeywordIntentClassifier
from jarvis.rules.catalog_vocabulary import CatalogVocabulary
from jarvis.rules.configuration_validator import ConfigurationValidator
from jarvis.services.configuration_assistant import ConfigurationAssistant
from tests.fakes import ScriptedChatClient, UnavailableChatClient


@pytest.fixture
def trace_store() -> InMemoryTraceStore:
    return InMemoryTraceStore(capacity=10)


@pytest.fixture
def create_assistant(
    hybrid_retriever: HybridRetriever,
    catalog_vocabulary: CatalogVocabulary,
    configuration_validator: ConfigurationValidator,
    trace_store: InMemoryTraceStore,
) -> Any:
    def create(chat_client: ScriptedChatClient) -> ConfigurationAssistant:
        return ConfigurationAssistant(
            intent_classifier=KeywordIntentClassifier(),
            retriever=hybrid_retriever,
            prompt_builder=PromptBuilder(catalog_vocabulary, history_turn_limit=4),
            chat_client=chat_client,
            catalog_vocabulary=catalog_vocabulary,
            configuration_validator=configuration_validator,
            trace_sink=trace_store,
        )

    return create


def test_greeting_skips_retrieval_and_language_model(
    create_assistant: Any, trace_store: InMemoryTraceStore
) -> None:
    chat_client = ScriptedChatClient({"reply": "unused"})

    response = create_assistant(chat_client).answer_question(AssistantRequest(question="hello"))

    assert response.intent is QueryIntent.GREETING
    assert chat_client.received_messages == []
    assert trace_store.find_trace(response.trace_id) is not None


def test_answer_is_grounded_traced_and_validated(
    create_assistant: Any, trace_store: InMemoryTraceStore
) -> None:
    chat_client = ScriptedChatClient(
        {
            "reply": "For logging I recommend the F-350 with the V8 and a manual gearbox.",
            "active_build": {
                "model": "F-350",
                "engine": "V8",
                "transmission": "manual",
                "application": "Logging",
            },
            "comparison": None,
            "cited_source_ids": ["RULE-LOGGING-RECOMMENDATION", "MADE-UP-ID"],
        }
    )

    response = create_assistant(chat_client).answer_question(
        AssistantRequest(
            question="What is the best truck for logging?", current_build=VehicleBuild(trim="Base")
        )
    )

    assert response.active_build == VehicleBuild(
        model="Ford F-350",
        engine="5.0L V8",
        transmission="6-Speed Manual",
        trim="Base",
        application="Logging",
    )
    assert response.validation.status is BuildStatus.INVALID
    assert "Engineering check:" in response.reply
    assert any(source.was_cited for source in response.sources)

    trace = trace_store.find_trace(response.trace_id)
    assert trace is not None
    assert trace.unknown_citation_ids == ["MADE-UP-ID"]
    assert trace.violated_rule_ids == ["RULE-V8-TRANSMISSION"]
    assert trace.language_model is not None and trace.language_model.reply_parsed
    assert "llm_generation" in trace.stage_durations_ms
    assert trace.context_documents


def test_unparseable_model_output_is_traced_but_still_answered(
    create_assistant: Any, trace_store: InMemoryTraceStore
) -> None:
    response = create_assistant(ScriptedChatClient("plain text answer")).answer_question(
        AssistantRequest(question="Tell me about towing on the RAM 2500")
    )

    trace = trace_store.find_trace(response.trace_id)
    assert response.reply == "plain text answer"
    assert trace is not None and trace.language_model is not None
    assert trace.language_model.reply_parsed is False


def test_language_model_failure_is_recorded_in_trace(
    create_assistant: Any, trace_store: InMemoryTraceStore
) -> None:
    with pytest.raises(LanguageModelUnavailableError):
        create_assistant(UnavailableChatClient()).answer_question(
            AssistantRequest(question="Price of the F-350?")
        )

    failed_trace = trace_store.list_recent_traces(limit=1)[0]
    assert failed_trace.error == "Connection refused"
    assert failed_trace.context_documents
