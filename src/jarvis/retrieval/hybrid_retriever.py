from dataclasses import dataclass, field
from typing import Any

from jarvis.domain.conversation import QueryIntent
from jarvis.domain.knowledge import ScoredDocument
from jarvis.observability.timing import record_stage_duration
from jarvis.retrieval.embeddings import EmbeddingModel
from jarvis.retrieval.keyword_index import BM25KeywordIndex
from jarvis.retrieval.query_analysis import MetadataFilterExtractor
from jarvis.retrieval.rank_fusion import fuse_rankings_with_reciprocal_rank
from jarvis.retrieval.reranking import DocumentReranker
from jarvis.retrieval.vector_store import ChromaVectorStore


@dataclass(frozen=True)
class RetrievalSettings:
    candidate_count: int = 20
    rerank_candidate_count: int = 20
    context_document_count: int = 5
    rrf_rank_constant: int = 60


@dataclass
class RetrievalResult:
    context_documents: list[ScoredDocument]
    candidates_by_channel: dict[str, list[ScoredDocument]]
    fused_candidates: list[ScoredDocument]
    applied_filters: dict[str, Any]
    stage_durations_ms: dict[str, float] = field(default_factory=dict)


class HybridRetriever:
    def __init__(
        self,
        embedding_model: EmbeddingModel,
        vector_store: ChromaVectorStore,
        keyword_index: BM25KeywordIndex,
        filter_extractor: MetadataFilterExtractor,
        reranker: DocumentReranker,
        retrieval_settings: RetrievalSettings,
    ) -> None:
        self._embedding_model = embedding_model
        self._vector_store = vector_store
        self._keyword_index = keyword_index
        self._filter_extractor = filter_extractor
        self._reranker = reranker
        self._settings = retrieval_settings

    def retrieve_context(self, question: str, intent: QueryIntent) -> RetrievalResult:
        stage_durations_ms: dict[str, float] = {}
        candidate_count = self._settings.candidate_count

        with record_stage_duration(stage_durations_ms, "query_embedding"):
            query_vector = self._embedding_model.embed_query(question)

        with record_stage_duration(stage_durations_ms, "vector_search"):
            candidates_by_channel = {
                "vector": self._vector_store.search_similar_documents(query_vector, candidate_count)
            }

        with record_stage_duration(stage_durations_ms, "keyword_search"):
            candidates_by_channel["keyword"] = self._keyword_index.search_by_keywords(
                question, candidate_count
            )

        structured_filters = self._filter_extractor.extract_filters(question, intent)
        with record_stage_duration(stage_durations_ms, "filtered_search"):
            for filter_name, metadata_filter in structured_filters.list_named_filters().items():
                candidates_by_channel[f"filter:{filter_name}"] = self._vector_store.search_similar_documents(
                    query_vector, candidate_count, metadata_filter
                )

        fused_candidates = fuse_rankings_with_reciprocal_rank(
            candidates_by_channel, self._settings.rrf_rank_constant
        )

        with record_stage_duration(stage_durations_ms, "reranking"):
            context_documents = self._reranker.rerank_documents(
                question,
                fused_candidates[: self._settings.rerank_candidate_count],
                self._settings.context_document_count,
            )

        return RetrievalResult(
            context_documents=context_documents,
            candidates_by_channel=candidates_by_channel,
            fused_candidates=fused_candidates,
            applied_filters=structured_filters.describe(),
            stage_durations_ms=stage_durations_ms,
        )
