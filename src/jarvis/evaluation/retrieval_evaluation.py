import json
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from jarvis.domain.conversation import QueryIntent
from jarvis.retrieval.hybrid_retriever import HybridRetriever
from jarvis.retrieval.query_analysis import KeywordIntentClassifier


class GoldenQuery(BaseModel):
    query_id: str
    question: str
    relevant_document_ids: list[str] = Field(min_length=1)
    expected_intent: QueryIntent | None = None


class QueryEvaluationResult(BaseModel):
    query_id: str
    question: str
    predicted_intent: QueryIntent
    expected_intent: QueryIntent | None
    retrieved_document_ids: list[str]
    relevant_document_ids: list[str]
    first_relevant_rank: int | None
    recall_at_k: float
    candidate_recall: float

    @property
    def is_hit(self) -> bool:
        return self.first_relevant_rank is not None

    @property
    def reciprocal_rank(self) -> float:
        return 1.0 / self.first_relevant_rank if self.first_relevant_rank else 0.0


class RetrievalEvaluationReport(BaseModel):
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    top_k: int
    query_count: int
    hit_rate_at_k: float
    mean_recall_at_k: float
    mean_reciprocal_rank: float
    mean_candidate_recall: float
    intent_accuracy: float
    results: list[QueryEvaluationResult]

    def render_markdown_summary(self) -> str:
        summary_lines = [
            f"| Metric | Value (k={self.top_k}, n={self.query_count}) |",
            "|---|---|",
            f"| Hit rate@k | {self.hit_rate_at_k:.2f} |",
            f"| Recall@k | {self.mean_recall_at_k:.2f} |",
            f"| MRR | {self.mean_reciprocal_rank:.2f} |",
            f"| Candidate recall (before rerank) | {self.mean_candidate_recall:.2f} |",
            f"| Intent accuracy | {self.intent_accuracy:.2f} |",
        ]
        missed_queries = [result for result in self.results if not result.is_hit]
        if missed_queries:
            summary_lines += ["", "Missed queries:"]
            summary_lines += [f"- `{result.query_id}` {result.question}" for result in missed_queries]
        return "\n".join(summary_lines)


def load_golden_queries(golden_set_path: Path) -> list[GoldenQuery]:
    with golden_set_path.open(encoding="utf-8") as golden_set_file:
        return [GoldenQuery.model_validate(entry) for entry in json.load(golden_set_file)]


def _calculate_capped_recall(found_ids: list[str], relevant_ids: set[str], top_k: int) -> float:
    found_relevant_count = len(relevant_ids.intersection(found_ids))
    return found_relevant_count / min(len(relevant_ids), top_k)


class RetrievalEvaluator:
    def __init__(self, retriever: HybridRetriever, intent_classifier: KeywordIntentClassifier) -> None:
        self._retriever = retriever
        self._intent_classifier = intent_classifier

    def evaluate_golden_queries(self, golden_queries: list[GoldenQuery]) -> RetrievalEvaluationReport:
        results = [self._evaluate_single_query(golden_query) for golden_query in golden_queries]
        top_k = max((len(result.retrieved_document_ids) for result in results), default=0)
        query_count = len(results) or 1
        intent_checked_results = [result for result in results if result.expected_intent is not None]

        return RetrievalEvaluationReport(
            top_k=top_k,
            query_count=len(results),
            hit_rate_at_k=sum(result.is_hit for result in results) / query_count,
            mean_recall_at_k=sum(result.recall_at_k for result in results) / query_count,
            mean_reciprocal_rank=sum(result.reciprocal_rank for result in results) / query_count,
            mean_candidate_recall=sum(result.candidate_recall for result in results) / query_count,
            intent_accuracy=(
                sum(result.predicted_intent == result.expected_intent for result in intent_checked_results)
                / len(intent_checked_results)
                if intent_checked_results
                else 0.0
            ),
            results=results,
        )

    def _evaluate_single_query(self, golden_query: GoldenQuery) -> QueryEvaluationResult:
        predicted_intent = self._intent_classifier.classify_intent(golden_query.question)
        retrieval_result = self._retriever.retrieve_context(golden_query.question, predicted_intent)
        retrieved_ids = [scored.document.document_id for scored in retrieval_result.context_documents]
        candidate_ids = [scored.document.document_id for scored in retrieval_result.fused_candidates]
        relevant_ids = set(golden_query.relevant_document_ids)
        top_k = max(len(retrieved_ids), 1)

        first_relevant_rank = next(
            (rank for rank, document_id in enumerate(retrieved_ids, start=1) if document_id in relevant_ids),
            None,
        )
        return QueryEvaluationResult(
            query_id=golden_query.query_id,
            question=golden_query.question,
            predicted_intent=predicted_intent,
            expected_intent=golden_query.expected_intent,
            retrieved_document_ids=retrieved_ids,
            relevant_document_ids=golden_query.relevant_document_ids,
            first_relevant_rank=first_relevant_rank,
            recall_at_k=_calculate_capped_recall(retrieved_ids, relevant_ids, top_k),
            candidate_recall=_calculate_capped_recall(
                candidate_ids, relevant_ids, max(len(candidate_ids), 1)
            ),
        )


def save_evaluation_report(report: RetrievalEvaluationReport, report_directory: Path) -> Path:
    report_directory.mkdir(parents=True, exist_ok=True)
    report_path = report_directory / f"retrieval_report_{report.generated_at:%Y%m%d_%H%M%S}.json"
    report_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report_path
