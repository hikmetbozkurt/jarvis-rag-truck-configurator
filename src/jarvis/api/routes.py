from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from jarvis.api.schemas import ChatRequest, ErrorResponse, HealthResponse, ReadinessResponse
from jarvis.bootstrap import ApplicationContainer
from jarvis.domain.conversation import AssistantRequest, AssistantResponse
from jarvis.generation.llm_clients import LanguageModelUnavailableError
from jarvis.observability.tracing import RequestTrace

api_router = APIRouter(prefix="/api/v1")


def get_application_container(request: Request) -> ApplicationContainer:
    container: ApplicationContainer = request.app.state.container
    return container


ContainerDependency = Annotated[ApplicationContainer, Depends(get_application_container)]


@api_router.get("/health", response_model=HealthResponse, tags=["operations"])
def report_liveness() -> HealthResponse:
    return HealthResponse(status="ok")


@api_router.get("/ready", response_model=ReadinessResponse, tags=["operations"])
def report_readiness(container: ContainerDependency) -> ReadinessResponse:
    indexed_document_count = container.vector_store.count_documents()
    language_model_reachable = container.chat_client.is_model_reachable()
    is_ready = indexed_document_count > 0 and language_model_reachable
    return ReadinessResponse(
        status="ready" if is_ready else "degraded",
        indexed_document_count=indexed_document_count,
        language_model_provider=container.chat_client.provider_name,
        language_model_name=container.chat_client.model_name,
        language_model_reachable=language_model_reachable,
    )


@api_router.post(
    "/chat",
    response_model=AssistantResponse,
    responses={503: {"model": ErrorResponse}},
    tags=["assistant"],
)
def answer_chat_message(chat_request: ChatRequest, container: ContainerDependency) -> AssistantResponse:
    if container.vector_store.count_documents() == 0:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The knowledge base is empty. Run `jarvis ingest` first.",
        )
    try:
        return container.assistant.answer_question(
            AssistantRequest(
                question=chat_request.message,
                history=chat_request.history,
                current_build=chat_request.active_build,
                session_id=chat_request.session_id,
            )
        )
    except LanguageModelUnavailableError as unavailable_error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(unavailable_error)
        ) from None


@api_router.get("/traces", response_model=list[RequestTrace], tags=["observability"])
def list_recent_traces(
    container: ContainerDependency, limit: Annotated[int, Query(ge=1, le=200)] = 20
) -> list[RequestTrace]:
    return container.trace_store.list_recent_traces(limit)


@api_router.get("/traces/{trace_id}", response_model=RequestTrace, tags=["observability"])
def read_trace(trace_id: str, container: ContainerDependency) -> RequestTrace:
    trace = container.trace_store.find_trace(trace_id)
    if trace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trace not found.")
    return trace
