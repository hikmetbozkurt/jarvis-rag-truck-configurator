from collections import Counter

from jarvis.domain.knowledge import KnowledgeDocument, SourceType


def test_every_dataset_is_loaded(knowledge_documents: list[KnowledgeDocument]) -> None:
    documents_per_source = Counter(document.source_type for document in knowledge_documents)

    assert documents_per_source[SourceType.EPA_INVENTORY] > 100
    assert documents_per_source[SourceType.TECHNICAL_MANUAL] == 13
    assert documents_per_source[SourceType.ENGINEERING_RULE] == 13
    assert documents_per_source[SourceType.MARKET_PRICING] == 6
    assert documents_per_source[SourceType.EFFICIENCY_SPEC] == 4
    assert documents_per_source[SourceType.SAFETY_WARRANTY] == 4


def test_document_ids_are_unique(knowledge_documents: list[KnowledgeDocument]) -> None:
    id_counts = Counter(document.document_id for document in knowledge_documents)

    assert [document_id for document_id, count in id_counts.items() if count > 1] == []


def test_pricing_documents_carry_numeric_metadata(knowledge_documents: list[KnowledgeDocument]) -> None:
    model_pricing = [
        document
        for document in knowledge_documents
        if document.source_type is SourceType.MARKET_PRICING
        and document.metadata.get("topic") == "model_pricing"
    ]

    assert len(model_pricing) == 4
    assert all(isinstance(document.metadata["min_price_usd"], int | float) for document in model_pricing)
    assert all("None" not in document.content for document in model_pricing)


def test_inventory_is_limited_to_pickups(knowledge_documents: list[KnowledgeDocument]) -> None:
    inventory = [
        document for document in knowledge_documents if document.source_type is SourceType.EPA_INVENTORY
    ]
    model_families = {document.metadata["model_family"] for document in inventory}

    assert all("Pickup" in document.content for document in inventory)
    assert {"F-150", "Silverado", "Ram 1500", "Tacoma"} <= model_families
