import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from jarvis.domain.knowledge import KnowledgeDocument, MetadataValue, SourceType


class DatasetFileMissingError(FileNotFoundError):
    pass


def read_json_dataset(dataset_path: Path) -> Any:
    if not dataset_path.exists():
        raise DatasetFileMissingError(
            f"{dataset_path} is missing. Run `Rscript run_all.R` inside data_generation/ to create it."
        )
    with dataset_path.open(encoding="utf-8") as dataset_file:
        return json.load(dataset_file)


def keep_scalar_metadata(record: dict[str, Any], field_names: tuple[str, ...]) -> dict[str, MetadataValue]:
    return {
        field_name: record[field_name]
        for field_name in field_names
        if isinstance(record.get(field_name), str | int | float | bool)
    }


class DocumentSource(ABC):
    file_name: str

    def __init__(self, data_directory: Path) -> None:
        self._dataset_path = data_directory / self.file_name

    @property
    def source_name(self) -> str:
        return type(self).__name__

    def load_documents(self) -> list[KnowledgeDocument]:
        return self._convert_records(read_json_dataset(self._dataset_path))

    @abstractmethod
    def _convert_records(self, dataset: Any) -> list[KnowledgeDocument]: ...


class EpaInventorySource(DocumentSource):
    file_name = "epa_pickup_inventory.json"
    metadata_fields = (
        "make",
        "model",
        "model_family",
        "year",
        "fuel_type",
        "cylinders",
        "displacement_l",
        "mpg_city",
        "mpg_highway",
        "mpg_combined",
    )

    def _convert_records(self, dataset: list[dict[str, Any]]) -> list[KnowledgeDocument]:
        return [
            KnowledgeDocument(
                document_id=record["id"],
                source_type=SourceType.EPA_INVENTORY,
                title=record["name"],
                content=record["content"],
                metadata=keep_scalar_metadata(record, self.metadata_fields),
            )
            for record in dataset
        ]


class TechnicalManualSource(DocumentSource):
    file_name = "technical_manual.json"

    def _convert_records(self, dataset: list[dict[str, Any]]) -> list[KnowledgeDocument]:
        return [
            KnowledgeDocument(
                document_id=record["id"],
                source_type=SourceType.TECHNICAL_MANUAL,
                title=record["title"],
                content=record["content"],
                metadata={"topic": record["topic"]},
            )
            for record in dataset
        ]


class VehicleCatalogSource(DocumentSource):
    file_name = "vehicle_catalog.json"

    def _convert_records(self, dataset: dict[str, Any]) -> list[KnowledgeDocument]:
        return self._describe_priced_options(dataset) + self._describe_rules(dataset["rules"])

    @staticmethod
    def _describe_priced_options(catalog: dict[str, Any]) -> list[KnowledgeDocument]:
        option_documents = []
        for category_name, label in (("transmissions", "Transmission"), ("trims", "Trim")):
            for option in catalog[category_name]:
                price_note = (
                    "included at no extra cost"
                    if option["price_adder_usd"] == 0
                    else f"adds ${option['price_adder_usd']:,} to the base price"
                )
                option_documents.append(
                    KnowledgeDocument(
                        document_id=f"CATALOG-{option['id']}",
                        source_type=SourceType.CATALOG_PART,
                        title=f"{label} option: {option['name']}",
                        content=f"{option['description']} The {option['name']} {price_note}.",
                        metadata={"category": category_name, "price_adder_usd": option["price_adder_usd"]},
                    )
                )
        return option_documents

    @staticmethod
    def _describe_rules(rules: list[dict[str, Any]]) -> list[KnowledgeDocument]:
        rule_documents = []
        for rule in rules:
            condition_text = " and ".join(
                f"{field} is {value}" for field, value in rule["conditions"].items()
            )
            rule_documents.append(
                KnowledgeDocument(
                    document_id=rule["id"],
                    source_type=SourceType.ENGINEERING_RULE,
                    title=f"Engineering {rule['type']}: when {condition_text}",
                    content=rule["message"],
                    metadata={"rule_type": rule["type"]},
                )
            )
        return rule_documents


class MarketPricingSource(DocumentSource):
    file_name = "market_pricing.json"
    metadata_fields = ("topic", "model_name", "base_price_usd", "min_price_usd", "max_price_usd")

    def _convert_records(self, dataset: list[dict[str, Any]]) -> list[KnowledgeDocument]:
        return [
            KnowledgeDocument(
                document_id=record["id"],
                source_type=SourceType.MARKET_PRICING,
                title=f"Pricing: {record.get('model_name') or record['topic'].replace('_', ' ')}",
                content=record["content"],
                metadata=keep_scalar_metadata(record, self.metadata_fields),
            )
            for record in dataset
        ]


class EfficiencySpecsSource(DocumentSource):
    file_name = "efficiency_specs.json"

    def _convert_records(self, dataset: list[dict[str, Any]]) -> list[KnowledgeDocument]:
        return [
            KnowledgeDocument(
                document_id=record["id"],
                source_type=SourceType.EFFICIENCY_SPEC,
                title=f"Efficiency: {record['engine_name']}",
                content=record["content"],
                metadata=keep_scalar_metadata(
                    record, ("engine_name", "rating", "combined_mpg", "range_miles")
                ),
            )
            for record in dataset
        ]


class SafetyWarrantySource(DocumentSource):
    file_name = "safety_warranty.json"

    def _convert_records(self, dataset: list[dict[str, Any]]) -> list[KnowledgeDocument]:
        return [
            KnowledgeDocument(
                document_id=record["id"],
                source_type=SourceType.SAFETY_WARRANTY,
                title=record["topic"],
                content=record["content"],
            )
            for record in dataset
        ]


def create_default_document_sources(data_directory: Path) -> list[DocumentSource]:
    return [
        EpaInventorySource(data_directory),
        TechnicalManualSource(data_directory),
        VehicleCatalogSource(data_directory),
        MarketPricingSource(data_directory),
        EfficiencySpecsSource(data_directory),
        SafetyWarrantySource(data_directory),
    ]
