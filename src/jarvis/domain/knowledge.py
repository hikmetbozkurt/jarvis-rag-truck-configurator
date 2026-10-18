from enum import StrEnum

from pydantic import BaseModel, Field

MetadataValue = str | int | float | bool


class SourceType(StrEnum):
    EPA_INVENTORY = "epa_inventory"
    TECHNICAL_MANUAL = "technical_manual"
    CATALOG_PART = "catalog_part"
    ENGINEERING_RULE = "engineering_rule"
    MARKET_PRICING = "market_pricing"
    EFFICIENCY_SPEC = "efficiency_spec"
    SAFETY_WARRANTY = "safety_warranty"


class KnowledgeDocument(BaseModel):
    document_id: str
    source_type: SourceType
    title: str
    content: str
    metadata: dict[str, MetadataValue] = Field(default_factory=dict)

    @property
    def searchable_text(self) -> str:
        return f"{self.title}\n{self.content}"


class ScoredDocument(BaseModel):
    document: KnowledgeDocument
    score: float
    rank: int
