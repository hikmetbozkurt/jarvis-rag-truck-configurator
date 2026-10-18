import logging
from collections import Counter
from dataclasses import dataclass, field

from jarvis.domain.knowledge import KnowledgeDocument
from jarvis.ingestion.document_sources import DocumentSource
from jarvis.retrieval.embeddings import EmbeddingModel
from jarvis.retrieval.vector_store import ChromaVectorStore

logger = logging.getLogger(__name__)


class DuplicateDocumentIdError(ValueError):
    pass


@dataclass
class IngestionReport:
    document_count_by_source: dict[str, int] = field(default_factory=dict)
    was_skipped: bool = False

    @property
    def total_document_count(self) -> int:
        return sum(self.document_count_by_source.values())


class KnowledgeBaseBuilder:
    def __init__(
        self,
        document_sources: list[DocumentSource],
        embedding_model: EmbeddingModel,
        vector_store: ChromaVectorStore,
    ) -> None:
        self._document_sources = document_sources
        self._embedding_model = embedding_model
        self._vector_store = vector_store

    def build_knowledge_base(self, skip_if_populated: bool = False) -> IngestionReport:
        if skip_if_populated and self._vector_store.count_documents() > 0:
            logger.info(
                "Vector store already holds %d documents, skipping ingestion.",
                self._vector_store.count_documents(),
            )
            return IngestionReport(was_skipped=True)

        report = IngestionReport()
        documents: list[KnowledgeDocument] = []
        for document_source in self._document_sources:
            source_documents = document_source.load_documents()
            report.document_count_by_source[document_source.source_name] = len(source_documents)
            documents.extend(source_documents)

        self._ensure_unique_document_ids(documents)
        logger.info("Embedding %d documents.", len(documents))
        vectors = self._embedding_model.embed_documents([document.searchable_text for document in documents])

        self._vector_store.delete_all_documents()
        self._vector_store.add_documents(documents, vectors)
        logger.info("Knowledge base ready with %d documents.", report.total_document_count)
        return report

    @staticmethod
    def _ensure_unique_document_ids(documents: list[KnowledgeDocument]) -> None:
        id_counts = Counter(document.document_id for document in documents)
        duplicate_ids = sorted(document_id for document_id, count in id_counts.items() if count > 1)
        if duplicate_ids:
            raise DuplicateDocumentIdError(f"Duplicate document ids: {', '.join(duplicate_ids)}")
