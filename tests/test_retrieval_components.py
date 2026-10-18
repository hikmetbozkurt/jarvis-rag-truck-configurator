from jarvis.domain.conversation import QueryIntent
from jarvis.domain.knowledge import KnowledgeDocument, ScoredDocument, SourceType
from jarvis.retrieval.hybrid_retriever import HybridRetriever
from jarvis.retrieval.keyword_index import BM25KeywordIndex, tokenize_for_keyword_search
from jarvis.retrieval.rank_fusion import fuse_rankings_with_reciprocal_rank


def make_scored_document(document_id: str, rank: int) -> ScoredDocument:
    document = KnowledgeDocument(
        document_id=document_id,
        source_type=SourceType.TECHNICAL_MANUAL,
        title=document_id,
        content=document_id,
    )
    return ScoredDocument(document=document, score=1.0, rank=rank)


def test_tokenizer_keeps_model_names_searchable_with_and_without_hyphen() -> None:
    tokens = tokenize_for_keyword_search("Is the F-150 offered with the 5.0L V8?")

    assert {"f-150", "f150", "5.0l", "v8"} <= set(tokens)
    assert "the" not in tokens


def test_keyword_index_finds_exact_engineering_rule(knowledge_documents: list[KnowledgeDocument]) -> None:
    keyword_index = BM25KeywordIndex(knowledge_documents)

    top_hits = keyword_index.search_by_keywords("5.0L V8 with 6-Speed Manual", limit=3)

    assert "RULE-V8-TRANSMISSION" in [hit.document.document_id for hit in top_hits]


def test_reciprocal_rank_fusion_rewards_documents_found_by_several_channels() -> None:
    fused = fuse_rankings_with_reciprocal_rank(
        {
            "vector": [make_scored_document("A", 1), make_scored_document("B", 2)],
            "keyword": [make_scored_document("B", 1), make_scored_document("C", 2)],
        },
        rank_constant=60,
    )

    assert [candidate.document.document_id for candidate in fused] == ["B", "A", "C"]
    assert fused[0].score == round(1 / 62 + 1 / 61, 6)


def test_hybrid_retriever_reports_every_channel(hybrid_retriever: HybridRetriever) -> None:
    result = hybrid_retriever.retrieve_context(
        "Compare the 2019 F-150 and Silverado fuel economy", QueryIntent.COMPARISON
    )

    assert {"vector", "keyword", "filter:inventory:F-150", "filter:inventory:Silverado"} <= set(
        result.candidates_by_channel
    )
    assert len(result.context_documents) == 5
    assert set(result.stage_durations_ms) >= {
        "query_embedding",
        "vector_search",
        "keyword_search",
        "reranking",
    }


def test_hybrid_retriever_finds_the_logging_recommendation(hybrid_retriever: HybridRetriever) -> None:
    result = hybrid_retriever.retrieve_context(
        "What is the best truck for logging?", QueryIntent.CONFIGURATION
    )

    retrieved_ids = [scored.document.document_id for scored in result.context_documents]
    assert "RULE-LOGGING-RECOMMENDATION" in retrieved_ids
