import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from jarvis.domain.conversation import QueryIntent
from jarvis.domain.knowledge import KnowledgeDocument, SourceType
from jarvis.retrieval.vector_store import MetadataFilter

_GREETING_PATTERN = re.compile(
    r"^(hi|hello|hey|yo|sup|what's up|good (morning|afternoon|evening)|how are you|thanks|thank you)[\s!.?]*$"
)


def _compile_keyword_pattern(keywords: Iterable[str]) -> re.Pattern[str]:
    alternatives = "|".join(re.escape(keyword) for keyword in keywords)
    return re.compile(rf"(?<![a-z0-9])({alternatives})(?![a-z0-9])")


_COMPARISON_PATTERN = _compile_keyword_pattern(
    ["compare", "comparison", "vs", "vs.", "versus", "better than", "difference between", "which is better"]
)

_INTENT_KEYWORD_PATTERNS: list[tuple[QueryIntent, re.Pattern[str]]] = [
    (
        QueryIntent.PRICING,
        _compile_keyword_pattern(
            [
                "price",
                "pricing",
                "cost",
                "costs",
                "how much is",
                "how much are",
                "how much would",
                "budget",
                "cheap",
                "cheapest",
                "expensive",
                "msrp",
            ]
        ),
    ),
    (
        QueryIntent.WARRANTY_AND_SAFETY,
        _compile_keyword_pattern(
            ["warranty", "safety", "safe", "safest", "crash", "family", "kids", "child"]
        ),
    ),
    (
        QueryIntent.INVENTORY_SEARCH,
        _compile_keyword_pattern(
            ["find", "show me", "in stock", "inventory", "available", "looking for", "list"]
        ),
    ),
    (
        QueryIntent.TECHNICAL_SPECIFICATION,
        _compile_keyword_pattern(
            [
                "towing",
                "tow",
                "payload",
                "torque",
                "horsepower",
                "hp",
                "transmission",
                "engine",
                "mpg",
                "efficiency",
                "fuel economy",
                "range",
                "specs",
                "specification",
            ]
        ),
    ),
]

_YEAR_PATTERN = re.compile(r"(?<!\d)((?:19|20)\d{2})(?!\d)")
_MPG_AT_LEAST_PATTERN = re.compile(
    r"(?:over|above|at least|more than|greater than|better than)\s+(\d{1,2})\s*mpg"
)
_MPG_AT_MOST_PATTERN = re.compile(r"(?:under|below|less than|at most)\s+(\d{1,2})\s*mpg")
_PRICE_AT_MOST_PATTERN = re.compile(r"(?:under|below|less than|at most|max(?:imum)?)\s+\$\s?([\d,]+k?)")
_PRICE_AT_LEAST_PATTERN = re.compile(r"(?:over|above|more than|at least)\s+\$\s?([\d,]+k?)")
_MAKE_ALIASES = {"chevy": "Chevrolet"}
_INVENTORY_FILTER_INTENTS = frozenset(
    {QueryIntent.INVENTORY_SEARCH, QueryIntent.COMPARISON, QueryIntent.TECHNICAL_SPECIFICATION}
)
_MAKE_FILTER_INTENTS = frozenset({QueryIntent.INVENTORY_SEARCH, QueryIntent.COMPARISON})


class KeywordIntentClassifier:
    def classify_intent(self, question: str) -> QueryIntent:
        normalized_question = question.lower().strip()
        if _GREETING_PATTERN.match(normalized_question):
            return QueryIntent.GREETING
        if _COMPARISON_PATTERN.search(normalized_question):
            return QueryIntent.COMPARISON
        if _YEAR_PATTERN.search(normalized_question):
            return QueryIntent.INVENTORY_SEARCH
        for intent, keyword_pattern in _INTENT_KEYWORD_PATTERNS:
            if keyword_pattern.search(normalized_question):
                return intent
        return QueryIntent.CONFIGURATION


@dataclass(frozen=True)
class StructuredQueryFilters:
    inventory_filters: dict[str, MetadataFilter] = field(default_factory=dict)
    pricing_filter: MetadataFilter | None = None

    def list_named_filters(self) -> dict[str, MetadataFilter]:
        named_filters = {f"inventory:{label}": value for label, value in self.inventory_filters.items()}
        if self.pricing_filter is not None:
            named_filters["pricing"] = self.pricing_filter
        return named_filters

    def describe(self) -> dict[str, Any]:
        return dict(self.list_named_filters())


def combine_filter_conditions(conditions: list[MetadataFilter]) -> MetadataFilter:
    return conditions[0] if len(conditions) == 1 else {"$and": conditions}


def _compact_alphanumeric(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _parse_dollar_amount(raw_amount: str) -> int:
    digits = raw_amount.replace(",", "").lower()
    return int(digits[:-1]) * 1000 if digits.endswith("k") else int(digits)


class MetadataFilterExtractor:
    def __init__(self, known_makes: set[str], known_model_families: set[str]) -> None:
        self._makes_by_lowercase_name = {make.lower(): make for make in known_makes}
        self._model_families_by_compact_name = {
            _compact_alphanumeric(family): family for family in known_model_families if family
        }

    @classmethod
    def from_documents(cls, documents: list[KnowledgeDocument]) -> "MetadataFilterExtractor":
        inventory_metadata = [
            document.metadata for document in documents if document.source_type is SourceType.EPA_INVENTORY
        ]
        return cls(
            known_makes={str(metadata["make"]) for metadata in inventory_metadata if "make" in metadata},
            known_model_families={
                str(metadata["model_family"]) for metadata in inventory_metadata if "model_family" in metadata
            },
        )

    def extract_filters(self, question: str, intent: QueryIntent) -> StructuredQueryFilters:
        normalized_question = question.lower()
        inventory_filters = (
            self._build_inventory_filters(
                normalized_question, include_make_filters=intent in _MAKE_FILTER_INTENTS
            )
            if intent in _INVENTORY_FILTER_INTENTS
            else {}
        )
        return StructuredQueryFilters(
            inventory_filters=inventory_filters,
            pricing_filter=self._build_pricing_filter(normalized_question),
        )

    def _build_inventory_filters(
        self, normalized_question: str, include_make_filters: bool
    ) -> dict[str, MetadataFilter]:
        """Builds one filter per mentioned vehicle so a comparison retrieves evidence for every side.

        Questions about catalog models ("RAM 2500", "Ford F-350") also mention a make, so filtering by make
        alone is limited to inventory searches and comparisons; otherwise it floods the context with EPA rows.
        """
        shared_conditions: list[MetadataFilter] = []
        years = sorted({int(year) for year in _YEAR_PATTERN.findall(normalized_question)})
        if years:
            shared_conditions.append({"year": years[0]} if len(years) == 1 else {"year": {"$in": years}})
        if minimum_match := _MPG_AT_LEAST_PATTERN.search(normalized_question):
            shared_conditions.append({"mpg_combined": {"$gte": int(minimum_match.group(1))}})
        if maximum_match := _MPG_AT_MOST_PATTERN.search(normalized_question):
            shared_conditions.append({"mpg_combined": {"$lte": int(maximum_match.group(1))}})

        vehicle_conditions = {
            family: {"model_family": family} for family in self._find_model_families(normalized_question)
        }
        if not vehicle_conditions and include_make_filters:
            vehicle_conditions = {make: {"make": make} for make in self._find_makes(normalized_question)}
        if not vehicle_conditions and shared_conditions:
            vehicle_conditions = {"any": {}}

        inventory_condition = {"source_type": SourceType.EPA_INVENTORY.value}
        return {
            label: combine_filter_conditions(
                [inventory_condition, *([vehicle_condition] if vehicle_condition else []), *shared_conditions]
            )
            for label, vehicle_condition in vehicle_conditions.items()
        }

    @staticmethod
    def _build_pricing_filter(normalized_question: str) -> MetadataFilter | None:
        conditions: list[MetadataFilter] = []
        if budget_match := _PRICE_AT_MOST_PATTERN.search(normalized_question):
            conditions.append({"min_price_usd": {"$lte": _parse_dollar_amount(budget_match.group(1))}})
        if floor_match := _PRICE_AT_LEAST_PATTERN.search(normalized_question):
            conditions.append({"max_price_usd": {"$gte": _parse_dollar_amount(floor_match.group(1))}})
        if not conditions:
            return None
        return combine_filter_conditions([{"source_type": SourceType.MARKET_PRICING.value}, *conditions])

    def _find_model_families(self, normalized_question: str) -> list[str]:
        compact_question = _compact_alphanumeric(normalized_question)
        return sorted(
            family
            for compact_family, family in self._model_families_by_compact_name.items()
            if compact_family in compact_question
        )

    def _find_makes(self, normalized_question: str) -> list[str]:
        question_words = set(re.findall(r"[a-z]+", normalized_question))
        makes = {
            self._makes_by_lowercase_name[word]
            for word in question_words
            if word in self._makes_by_lowercase_name
        }
        makes.update(_MAKE_ALIASES[word] for word in question_words if word in _MAKE_ALIASES)
        return sorted(makes)
