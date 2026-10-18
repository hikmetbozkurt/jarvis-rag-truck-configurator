import pytest

from jarvis.domain.conversation import QueryIntent
from jarvis.domain.knowledge import KnowledgeDocument
from jarvis.retrieval.query_analysis import KeywordIntentClassifier, MetadataFilterExtractor


@pytest.mark.parametrize(
    ("question", "expected_intent"),
    [
        ("Hello!", QueryIntent.GREETING),
        ("Compare the F-150 and Silverado", QueryIntent.COMPARISON),
        ("Compare the 2019 Tacoma vs the 2020 Ranger", QueryIntent.COMPARISON),
        ("How much does the F-350 cost?", QueryIntent.PRICING),
        ("What warranty do you offer on the V8?", QueryIntent.WARRANTY_AND_SAFETY),
        ("Which truck is safest for my kids?", QueryIntent.WARRANTY_AND_SAFETY),
        ("Tell me about the 2017 RAM 2500", QueryIntent.INVENTORY_SEARCH),
        ("What is the towing capacity of the RAM 2500?", QueryIntent.TECHNICAL_SPECIFICATION),
        ("What is the best truck for logging?", QueryIntent.CONFIGURATION),
        ("I need a workhorse for my farm", QueryIntent.CONFIGURATION),
    ],
)
def test_classify_intent(question: str, expected_intent: QueryIntent) -> None:
    assert KeywordIntentClassifier().classify_intent(question) is expected_intent


@pytest.fixture(scope="module")
def filter_extractor(knowledge_documents: list[KnowledgeDocument]) -> MetadataFilterExtractor:
    return MetadataFilterExtractor.from_documents(knowledge_documents)


def test_year_and_model_family_become_one_inventory_filter(filter_extractor: MetadataFilterExtractor) -> None:
    filters = filter_extractor.extract_filters(
        "Show me 2019 Toyota Tacoma options", QueryIntent.INVENTORY_SEARCH
    )

    assert filters.inventory_filters == {
        "Tacoma": {"$and": [{"source_type": "epa_inventory"}, {"model_family": "Tacoma"}, {"year": 2019}]}
    }
    assert filters.pricing_filter is None


def test_comparison_creates_one_filter_per_vehicle(filter_extractor: MetadataFilterExtractor) -> None:
    filters = filter_extractor.extract_filters("Compare the F150 and the Silverado", QueryIntent.COMPARISON)

    assert set(filters.inventory_filters) == {"F-150", "Silverado"}


def test_make_alias_is_used_when_no_model_family_is_named(filter_extractor: MetadataFilterExtractor) -> None:
    filters = filter_extractor.extract_filters(
        "Any chevy pickups above 20 mpg?", QueryIntent.INVENTORY_SEARCH
    )

    assert filters.inventory_filters == {
        "Chevrolet": {
            "$and": [
                {"source_type": "epa_inventory"},
                {"make": "Chevrolet"},
                {"mpg_combined": {"$gte": 20}},
            ]
        }
    }


def test_budget_becomes_pricing_filter(filter_extractor: MetadataFilterExtractor) -> None:
    filters = filter_extractor.extract_filters("Is there anything under $45,000?", QueryIntent.PRICING)

    assert filters.pricing_filter == {
        "$and": [{"source_type": "market_pricing"}, {"min_price_usd": {"$lte": 45000}}]
    }


def test_question_without_structure_has_no_filters(filter_extractor: MetadataFilterExtractor) -> None:
    filters = filter_extractor.extract_filters("What is best for logging?", QueryIntent.CONFIGURATION)

    assert filters.list_named_filters() == {}


def test_catalog_question_does_not_trigger_inventory_make_filter(
    filter_extractor: MetadataFilterExtractor,
) -> None:
    filters = filter_extractor.extract_filters(
        "What is the towing capacity of the RAM 2500?", QueryIntent.TECHNICAL_SPECIFICATION
    )

    assert filters.inventory_filters == {}
