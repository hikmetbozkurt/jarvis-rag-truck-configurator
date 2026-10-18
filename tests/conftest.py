import uuid
from pathlib import Path

import pytest

from jarvis.config import PROJECT_ROOT
from jarvis.domain.knowledge import KnowledgeDocument
from jarvis.ingestion.document_sources import create_default_document_sources
from jarvis.ingestion.knowledge_base_builder import KnowledgeBaseBuilder
from jarvis.retrieval.hybrid_retriever import HybridRetriever, RetrievalSettings
from jarvis.retrieval.keyword_index import BM25KeywordIndex
from jarvis.retrieval.query_analysis import MetadataFilterExtractor
from jarvis.retrieval.reranking import FusedOrderReranker
from jarvis.retrieval.vector_store import ChromaVectorStore
from jarvis.rules.catalog_vocabulary import CatalogVocabulary
from jarvis.rules.configuration_validator import ConfigurationValidator
from tests.fakes import HashedBagOfWordsEmbeddingModel

DATA_DIRECTORY = PROJECT_ROOT / "data"
CATALOG_PATH = DATA_DIRECTORY / "vehicle_catalog.json"


@pytest.fixture(scope="session")
def data_directory() -> Path:
    return DATA_DIRECTORY


@pytest.fixture(scope="session")
def knowledge_documents() -> list[KnowledgeDocument]:
    documents: list[KnowledgeDocument] = []
    for document_source in create_default_document_sources(DATA_DIRECTORY):
        documents.extend(document_source.load_documents())
    return documents


@pytest.fixture(scope="session")
def catalog_vocabulary() -> CatalogVocabulary:
    return CatalogVocabulary.from_catalog_file(CATALOG_PATH)


@pytest.fixture(scope="session")
def configuration_validator() -> ConfigurationValidator:
    return ConfigurationValidator.from_catalog_file(CATALOG_PATH)


@pytest.fixture(scope="session")
def embedding_model() -> HashedBagOfWordsEmbeddingModel:
    return HashedBagOfWordsEmbeddingModel()


@pytest.fixture(scope="session")
def populated_vector_store(embedding_model: HashedBagOfWordsEmbeddingModel) -> ChromaVectorStore:
    vector_store = ChromaVectorStore.open_in_memory(f"test-{uuid.uuid4().hex[:8]}")
    KnowledgeBaseBuilder(
        create_default_document_sources(DATA_DIRECTORY), embedding_model, vector_store
    ).build_knowledge_base()
    return vector_store


@pytest.fixture(scope="session")
def hybrid_retriever(
    populated_vector_store: ChromaVectorStore, embedding_model: HashedBagOfWordsEmbeddingModel
) -> HybridRetriever:
    stored_documents = populated_vector_store.fetch_all_documents()
    return HybridRetriever(
        embedding_model=embedding_model,
        vector_store=populated_vector_store,
        keyword_index=BM25KeywordIndex(stored_documents),
        filter_extractor=MetadataFilterExtractor.from_documents(stored_documents),
        reranker=FusedOrderReranker(),
        retrieval_settings=RetrievalSettings(),
    )
