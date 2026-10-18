from pathlib import Path
from typing import Any

import chromadb

from jarvis.domain.knowledge import KnowledgeDocument, ScoredDocument, SourceType

MetadataFilter = dict[str, Any]

_RESERVED_METADATA_KEYS = ("source_type", "title")
_WRITE_BATCH_SIZE = 256


class ChromaVectorStore:
    def __init__(self, client: Any, collection_name: str) -> None:
        self._client = client
        self._collection_name = collection_name
        self._collection = self._open_collection()

    @classmethod
    def open_persistent(cls, storage_directory: Path, collection_name: str) -> "ChromaVectorStore":
        storage_directory.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(
            path=str(storage_directory),
            settings=chromadb.Settings(anonymized_telemetry=False),
        )
        return cls(client, collection_name)

    @classmethod
    def open_in_memory(cls, collection_name: str) -> "ChromaVectorStore":
        client = chromadb.EphemeralClient(settings=chromadb.Settings(anonymized_telemetry=False))
        return cls(client, collection_name)

    def _open_collection(self) -> Any:
        return self._client.get_or_create_collection(
            self._collection_name,
            configuration={"hnsw": {"space": "cosine"}},
            embedding_function=None,
        )

    def count_documents(self) -> int:
        return int(self._collection.count())

    def delete_all_documents(self) -> None:
        self._client.delete_collection(self._collection_name)
        self._collection = self._open_collection()

    def add_documents(self, documents: list[KnowledgeDocument], vectors: list[list[float]]) -> None:
        for batch_start in range(0, len(documents), _WRITE_BATCH_SIZE):
            batch_documents = documents[batch_start : batch_start + _WRITE_BATCH_SIZE]
            self._collection.add(
                ids=[document.document_id for document in batch_documents],
                documents=[document.content for document in batch_documents],
                metadatas=[self._to_chroma_metadata(document) for document in batch_documents],
                embeddings=vectors[batch_start : batch_start + _WRITE_BATCH_SIZE],
            )

    def search_similar_documents(
        self, query_vector: list[float], limit: int, metadata_filter: MetadataFilter | None = None
    ) -> list[ScoredDocument]:
        if self.count_documents() == 0:
            return []
        query_result = self._collection.query(
            query_embeddings=[query_vector],
            n_results=limit,
            where=metadata_filter,
            include=["documents", "metadatas", "distances"],
        )
        scored_documents = []
        for rank, (document_id, content, metadata, distance) in enumerate(
            zip(
                query_result["ids"][0],
                query_result["documents"][0],
                query_result["metadatas"][0],
                query_result["distances"][0],
                strict=True,
            ),
            start=1,
        ):
            scored_documents.append(
                ScoredDocument(
                    document=self._to_knowledge_document(document_id, content, metadata),
                    score=round(1.0 - float(distance), 6),
                    rank=rank,
                )
            )
        return scored_documents

    def fetch_all_documents(self) -> list[KnowledgeDocument]:
        stored_records = self._collection.get(include=["documents", "metadatas"])
        return [
            self._to_knowledge_document(document_id, content, metadata)
            for document_id, content, metadata in zip(
                stored_records["ids"], stored_records["documents"], stored_records["metadatas"], strict=True
            )
        ]

    @staticmethod
    def _to_chroma_metadata(document: KnowledgeDocument) -> dict[str, Any]:
        return {**document.metadata, "source_type": document.source_type.value, "title": document.title}

    @staticmethod
    def _to_knowledge_document(document_id: str, content: str, metadata: dict[str, Any]) -> KnowledgeDocument:
        return KnowledgeDocument(
            document_id=document_id,
            source_type=SourceType(metadata["source_type"]),
            title=str(metadata["title"]),
            content=content,
            metadata={key: value for key, value in metadata.items() if key not in _RESERVED_METADATA_KEYS},
        )
