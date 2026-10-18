from typing import Any

from jarvis.observability.tracing import RequestTrace


class LangfuseTraceSink:
    """Sends finished request traces to Langfuse. Credentials come from LANGFUSE_* variables."""

    def __init__(self) -> None:
        try:
            from langfuse import Langfuse
        except ImportError as import_error:
            raise RuntimeError(
                'Langfuse export is enabled but the package is missing. Run `pip install -e ".[langfuse]"`.'
            ) from import_error
        self._langfuse_class = Langfuse
        self._client = Langfuse()

    def record_trace(self, trace: RequestTrace) -> None:
        langfuse_trace_id = self._langfuse_class.create_trace_id(seed=trace.trace_id)
        with self._client.start_as_current_observation(
            trace_context={"trace_id": langfuse_trace_id},
            name="jarvis-chat",
            as_type="chain",
            input=trace.question,
            metadata={
                "jarvis_trace_id": trace.trace_id,
                "session_id": trace.session_id,
                "intent": trace.intent,
                "stage_durations_ms": trace.stage_durations_ms,
            },
        ) as root_observation:
            self._export_retrieval(root_observation, trace)
            self._export_generation(root_observation, trace)
            root_observation.update(
                output={"validation_status": trace.validation_status, "error": trace.error},
                level="ERROR" if trace.error else "DEFAULT",
            )

    def flush_pending_traces(self) -> None:
        self._client.flush()

    @staticmethod
    def _export_retrieval(root_observation: Any, trace: RequestTrace) -> None:
        with root_observation.start_as_current_observation(
            name="hybrid-retrieval",
            as_type="retriever",
            input={"question": trace.question, "filters": trace.applied_filters},
            output=[hit.model_dump() for hit in trace.context_documents],
            metadata={
                "candidates_by_channel": {
                    channel_name: [hit.document_id for hit in hits]
                    for channel_name, hits in trace.candidates_by_channel.items()
                }
            },
        ):
            pass

    @staticmethod
    def _export_generation(root_observation: Any, trace: RequestTrace) -> None:
        if trace.language_model is None:
            return
        with root_observation.start_as_current_observation(
            name="structured-reply",
            as_type="generation",
            model=trace.language_model.model_name,
            input={"estimated_prompt_tokens": trace.language_model.estimated_prompt_tokens},
            output={
                "reply_parsed": trace.language_model.reply_parsed,
                "cited_source_ids": trace.cited_source_ids,
                "unknown_citation_ids": trace.unknown_citation_ids,
            },
        ):
            pass
