from jarvis.config import PROJECT_ROOT
from jarvis.domain.knowledge import KnowledgeDocument
from jarvis.evaluation.retrieval_evaluation import RetrievalEvaluator, load_golden_queries
from jarvis.retrieval.hybrid_retriever import HybridRetriever
from jarvis.retrieval.query_analysis import KeywordIntentClassifier

GOLDEN_SET_PATH = PROJECT_ROOT / "evaluation" / "golden_set.json"


def test_golden_set_only_references_existing_documents(knowledge_documents: list[KnowledgeDocument]) -> None:
    existing_ids = {document.document_id for document in knowledge_documents}

    missing_ids = {
        document_id
        for golden_query in load_golden_queries(GOLDEN_SET_PATH)
        for document_id in golden_query.relevant_document_ids
        if document_id not in existing_ids
    }

    assert missing_ids == set()


def test_evaluator_produces_consistent_metrics(hybrid_retriever: HybridRetriever) -> None:
    golden_queries = load_golden_queries(GOLDEN_SET_PATH)

    report = RetrievalEvaluator(hybrid_retriever, KeywordIntentClassifier()).evaluate_golden_queries(
        golden_queries
    )

    assert report.query_count == len(golden_queries)
    assert report.top_k == 5
    assert 0.0 <= report.mean_reciprocal_rank <= report.hit_rate_at_k <= 1.0
    assert report.intent_accuracy == 1.0
    assert "Hit rate@k" in report.render_markdown_summary()
