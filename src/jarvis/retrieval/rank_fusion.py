from jarvis.domain.knowledge import KnowledgeDocument, ScoredDocument


def fuse_rankings_with_reciprocal_rank(
    rankings_by_channel: dict[str, list[ScoredDocument]], rank_constant: int = 60
) -> list[ScoredDocument]:
    """Reciprocal Rank Fusion: score = sum(1 / (rank_constant + rank)) over every channel."""
    fused_scores: dict[str, float] = {}
    documents_by_id: dict[str, KnowledgeDocument] = {}

    for ranked_documents in rankings_by_channel.values():
        for scored_document in ranked_documents:
            document_id = scored_document.document.document_id
            documents_by_id[document_id] = scored_document.document
            fused_scores[document_id] = fused_scores.get(document_id, 0.0) + 1.0 / (
                rank_constant + scored_document.rank
            )

    ordered_document_ids = sorted(fused_scores, key=lambda document_id: -fused_scores[document_id])
    return [
        ScoredDocument(
            document=documents_by_id[document_id], score=round(fused_scores[document_id], 6), rank=rank
        )
        for rank, document_id in enumerate(ordered_document_ids, start=1)
    ]
