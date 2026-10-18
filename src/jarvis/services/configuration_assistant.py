import logging
import time

from jarvis.domain.configuration import BuildValidationResult, VehicleBuild
from jarvis.domain.conversation import (
    AssistantRequest,
    AssistantResponse,
    LanguageModelReply,
    QueryIntent,
    SourceReference,
)
from jarvis.domain.knowledge import ScoredDocument
from jarvis.generation.llm_clients import ChatCompletionClient, LanguageModelUnavailableError
from jarvis.generation.prompt_builder import PromptBuilder
from jarvis.generation.reply_parser import parse_language_model_reply
from jarvis.observability.timing import record_stage_duration
from jarvis.observability.tracing import LanguageModelCallTrace, RequestTrace, TraceSink
from jarvis.retrieval.hybrid_retriever import HybridRetriever
from jarvis.retrieval.query_analysis import KeywordIntentClassifier
from jarvis.rules.catalog_vocabulary import CatalogVocabulary
from jarvis.rules.configuration_validator import ConfigurationValidator

logger = logging.getLogger(__name__)

GREETING_REPLY = (
    "Hello, I'm Jarvis. I can help you configure a pickup for your work, check engineering constraints "
    "and compare real-world EPA fuel economy. What will the truck be used for?"
)
_CHARACTERS_PER_TOKEN_ESTIMATE = 4


class ConfigurationAssistant:
    def __init__(
        self,
        intent_classifier: KeywordIntentClassifier,
        retriever: HybridRetriever,
        prompt_builder: PromptBuilder,
        chat_client: ChatCompletionClient,
        catalog_vocabulary: CatalogVocabulary,
        configuration_validator: ConfigurationValidator,
        trace_sink: TraceSink,
    ) -> None:
        self._intent_classifier = intent_classifier
        self._retriever = retriever
        self._prompt_builder = prompt_builder
        self._chat_client = chat_client
        self._catalog_vocabulary = catalog_vocabulary
        self._configuration_validator = configuration_validator
        self._trace_sink = trace_sink
        self._response_schema = prompt_builder.build_response_schema()

    def answer_question(self, request: AssistantRequest) -> AssistantResponse:
        started_at = time.perf_counter()
        trace = RequestTrace(question=request.question, session_id=request.session_id)
        try:
            trace.intent = self._intent_classifier.classify_intent(request.question)
            current_build = self._catalog_vocabulary.normalize_build(request.current_build)
            if trace.intent is QueryIntent.GREETING:
                response = self._build_greeting_response(current_build, trace)
            else:
                response = self._answer_with_retrieval(request, trace.intent, current_build, trace)
        except LanguageModelUnavailableError as unavailable_error:
            trace.error = str(unavailable_error)
            raise
        except Exception as unexpected_error:
            trace.error = f"{type(unexpected_error).__name__}: {unexpected_error}"
            logger.exception("Request %s failed", trace.trace_id)
            raise
        finally:
            trace.total_duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            self._trace_sink.record_trace(trace)

        response.latency_ms = trace.total_duration_ms
        return response

    def _build_greeting_response(self, current_build: VehicleBuild, trace: RequestTrace) -> AssistantResponse:
        validation = self._configuration_validator.validate_build(current_build)
        trace.validation_status = validation.status.value
        return AssistantResponse(
            reply=GREETING_REPLY,
            intent=QueryIntent.GREETING,
            active_build=current_build,
            validation=validation,
            trace_id=trace.trace_id,
            latency_ms=0.0,
        )

    def _answer_with_retrieval(
        self,
        request: AssistantRequest,
        intent: QueryIntent,
        current_build: VehicleBuild,
        trace: RequestTrace,
    ) -> AssistantResponse:
        retrieval_result = self._retriever.retrieve_context(request.question, intent)
        trace.applied_filters = retrieval_result.applied_filters
        trace.stage_durations_ms.update(retrieval_result.stage_durations_ms)
        trace.record_retrieval_candidates(
            retrieval_result.candidates_by_channel,
            retrieval_result.fused_candidates,
            retrieval_result.context_documents,
        )

        model_reply = self._generate_model_reply(
            request, intent, current_build, retrieval_result.context_documents, trace
        )

        updated_build = current_build.merge_with(
            self._catalog_vocabulary.normalize_build(model_reply.active_build)
        )
        validation = self._configuration_validator.validate_build(updated_build)
        trace.validation_status = validation.status.value
        trace.violated_rule_ids = [violation.rule_id for violation in validation.violations]

        context_document_ids = {scored.document.document_id for scored in retrieval_result.context_documents}
        trace.cited_source_ids = model_reply.cited_source_ids
        trace.unknown_citation_ids = [
            source_id for source_id in model_reply.cited_source_ids if source_id not in context_document_ids
        ]

        return AssistantResponse(
            reply=self._append_unmentioned_violations(model_reply.reply, validation),
            intent=intent,
            active_build=updated_build,
            validation=validation,
            comparison=model_reply.comparison,
            sources=self._describe_sources(retrieval_result.context_documents, model_reply.cited_source_ids),
            trace_id=trace.trace_id,
            latency_ms=0.0,
        )

    def _generate_model_reply(
        self,
        request: AssistantRequest,
        intent: QueryIntent,
        current_build: VehicleBuild,
        context_documents: list[ScoredDocument],
        trace: RequestTrace,
    ) -> LanguageModelReply:
        chat_messages = self._prompt_builder.build_chat_messages(
            request.question, intent, context_documents, request.history, current_build
        )
        prompt_character_count = sum(len(message["content"]) for message in chat_messages)
        trace.language_model = LanguageModelCallTrace(
            provider=self._chat_client.provider_name,
            model_name=self._chat_client.model_name,
            prompt_character_count=prompt_character_count,
            estimated_prompt_tokens=prompt_character_count // _CHARACTERS_PER_TOKEN_ESTIMATE,
        )

        with record_stage_duration(trace.stage_durations_ms, "llm_generation"):
            raw_output = self._chat_client.generate_structured_reply(chat_messages, self._response_schema)

        parsing_outcome = parse_language_model_reply(raw_output)
        trace.language_model.output_character_count = len(raw_output)
        trace.language_model.reply_parsed = parsing_outcome.succeeded
        trace.language_model.parse_error = parsing_outcome.error_message
        return parsing_outcome.reply

    @staticmethod
    def _append_unmentioned_violations(reply_text: str, validation: BuildValidationResult) -> str:
        unmentioned_messages = [
            violation.message for violation in validation.violations if violation.message not in reply_text
        ]
        if not unmentioned_messages:
            return reply_text
        warning_lines = "\n".join(f"- {message}" for message in unmentioned_messages)
        return f"{reply_text}\n\nEngineering check:\n{warning_lines}"

    @staticmethod
    def _describe_sources(
        context_documents: list[ScoredDocument], cited_source_ids: list[str]
    ) -> list[SourceReference]:
        cited_ids = set(cited_source_ids)
        return [
            SourceReference(
                document_id=scored.document.document_id,
                title=scored.document.title,
                source_type=scored.document.source_type,
                relevance_score=scored.score,
                was_cited=scored.document.document_id in cited_ids,
            )
            for scored in context_documents
        ]
