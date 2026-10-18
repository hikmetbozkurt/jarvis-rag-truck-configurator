import logging
from dataclasses import dataclass

from jarvis.config import LanguageModelProvider, Settings
from jarvis.generation.llm_clients import ChatCompletionClient, OllamaChatClient, OpenAICompatibleChatClient
from jarvis.generation.prompt_builder import PromptBuilder
from jarvis.ingestion.document_sources import create_default_document_sources
from jarvis.ingestion.knowledge_base_builder import KnowledgeBaseBuilder
from jarvis.observability.langfuse_exporter import LangfuseTraceSink
from jarvis.observability.tracing import CompositeTraceSink, InMemoryTraceStore, JsonlTraceSink, TraceSink
from jarvis.retrieval.embeddings import EmbeddingModel, SentenceTransformerEmbeddingModel
from jarvis.retrieval.hybrid_retriever import HybridRetriever, RetrievalSettings
from jarvis.retrieval.keyword_index import BM25KeywordIndex
from jarvis.retrieval.query_analysis import KeywordIntentClassifier, MetadataFilterExtractor
from jarvis.retrieval.reranking import CrossEncoderReranker, DocumentReranker, FusedOrderReranker
from jarvis.retrieval.vector_store import ChromaVectorStore
from jarvis.rules.catalog_vocabulary import CatalogVocabulary
from jarvis.rules.configuration_validator import ConfigurationValidator
from jarvis.services.configuration_assistant import ConfigurationAssistant

logger = logging.getLogger(__name__)

CATALOG_FILE_NAME = "vehicle_catalog.json"


@dataclass
class ApplicationContainer:
    settings: Settings
    vector_store: ChromaVectorStore
    retriever: HybridRetriever
    chat_client: ChatCompletionClient
    assistant: ConfigurationAssistant
    trace_store: InMemoryTraceStore
    langfuse_sink: LangfuseTraceSink | None = None

    def shutdown(self) -> None:
        if self.langfuse_sink is not None:
            self.langfuse_sink.flush_pending_traces()


def create_embedding_model(settings: Settings) -> EmbeddingModel:
    return SentenceTransformerEmbeddingModel(settings.embedding_model_name)


def create_vector_store(settings: Settings) -> ChromaVectorStore:
    return ChromaVectorStore.open_persistent(settings.vector_store_directory, settings.collection_name)


def create_knowledge_base_builder(
    settings: Settings, embedding_model: EmbeddingModel, vector_store: ChromaVectorStore
) -> KnowledgeBaseBuilder:
    return KnowledgeBaseBuilder(
        create_default_document_sources(settings.data_directory), embedding_model, vector_store
    )


def create_chat_client(settings: Settings) -> ChatCompletionClient:
    if settings.llm_provider is LanguageModelProvider.OPENAI_COMPATIBLE:
        return OpenAICompatibleChatClient(
            base_url=settings.llm_base_url,
            model_name=settings.llm_model_name,
            temperature=settings.llm_temperature,
            timeout_seconds=settings.llm_request_timeout_seconds,
            api_key=settings.llm_api_key,
        )
    return OllamaChatClient(
        base_url=settings.llm_base_url,
        model_name=settings.llm_model_name,
        temperature=settings.llm_temperature,
        context_window_tokens=settings.llm_context_window_tokens,
        timeout_seconds=settings.llm_request_timeout_seconds,
    )


def create_hybrid_retriever(
    settings: Settings, embedding_model: EmbeddingModel, vector_store: ChromaVectorStore
) -> HybridRetriever:
    stored_documents = vector_store.fetch_all_documents()
    reranker: DocumentReranker = (
        CrossEncoderReranker(settings.reranker_model_name)
        if settings.reranker_enabled
        else FusedOrderReranker()
    )
    return HybridRetriever(
        embedding_model=embedding_model,
        vector_store=vector_store,
        keyword_index=BM25KeywordIndex(stored_documents),
        filter_extractor=MetadataFilterExtractor.from_documents(stored_documents),
        reranker=reranker,
        retrieval_settings=RetrievalSettings(
            candidate_count=settings.retrieval_candidate_count,
            rerank_candidate_count=settings.rerank_candidate_count,
            context_document_count=settings.context_document_count,
            rrf_rank_constant=settings.rrf_rank_constant,
        ),
    )


def build_application_container(settings: Settings) -> ApplicationContainer:
    embedding_model = create_embedding_model(settings)
    vector_store = create_vector_store(settings)

    if settings.auto_ingest_on_startup:
        create_knowledge_base_builder(settings, embedding_model, vector_store).build_knowledge_base(
            skip_if_populated=True
        )
    if vector_store.count_documents() == 0:
        logger.warning("The vector store is empty. Run `jarvis ingest` before asking questions.")

    trace_store = InMemoryTraceStore(settings.trace_memory_capacity)
    trace_sinks: list[TraceSink] = [trace_store, JsonlTraceSink(settings.trace_log_path)]
    langfuse_sink = LangfuseTraceSink() if settings.langfuse_enabled else None
    if langfuse_sink is not None:
        trace_sinks.append(langfuse_sink)

    catalog_path = settings.data_directory / CATALOG_FILE_NAME
    catalog_vocabulary = CatalogVocabulary.from_catalog_file(catalog_path)
    retriever = create_hybrid_retriever(settings, embedding_model, vector_store)
    chat_client = create_chat_client(settings)

    assistant = ConfigurationAssistant(
        intent_classifier=KeywordIntentClassifier(),
        retriever=retriever,
        prompt_builder=PromptBuilder(catalog_vocabulary, settings.conversation_history_turn_limit),
        chat_client=chat_client,
        catalog_vocabulary=catalog_vocabulary,
        configuration_validator=ConfigurationValidator.from_catalog_file(catalog_path),
        trace_sink=CompositeTraceSink(trace_sinks),
    )
    return ApplicationContainer(
        settings=settings,
        vector_store=vector_store,
        retriever=retriever,
        chat_client=chat_client,
        assistant=assistant,
        trace_store=trace_store,
        langfuse_sink=langfuse_sink,
    )
