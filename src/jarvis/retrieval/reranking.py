from typing import TYPE_CHECKING, Protocol

from jarvis.domain.knowledge import ScoredDocument

if TYPE_CHECKING:
    from sentence_transformers import CrossEncoder


class DocumentReranker(Protocol):
    def rerank_documents(
        self, question: str, candidates: list[ScoredDocument], limit: int
    ) -> list[ScoredDocument]: ...


class CrossEncoderReranker:
    def __init__(self, model_name: str) -> None:
        self._model_name = model_name
        self._model: CrossEncoder | None = None

    def _load_model(self) -> "CrossEncoder":
        if self._model is None:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self._model_name)
        return self._model

    def rerank_documents(
        self, question: str, candidates: list[ScoredDocument], limit: int
    ) -> list[ScoredDocument]:
        if not candidates:
            return []
        question_document_pairs = [(question, candidate.document.searchable_text) for candidate in candidates]
        relevance_scores = self._load_model().predict(question_document_pairs)
        ordered_pairs = sorted(
            zip(candidates, relevance_scores, strict=True),
            key=lambda candidate_and_score: -candidate_and_score[1],
        )
        return [
            ScoredDocument(document=candidate.document, score=round(float(relevance_score), 6), rank=rank)
            for rank, (candidate, relevance_score) in enumerate(ordered_pairs[:limit], start=1)
        ]


class FusedOrderReranker:
    def rerank_documents(
        self, question: str, candidates: list[ScoredDocument], limit: int
    ) -> list[ScoredDocument]:
        return candidates[:limit]
