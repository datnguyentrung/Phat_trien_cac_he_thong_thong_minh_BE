from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="ignore",
    )


class ProductPrice(ApiModel):
    amount: float
    currency: str | None = None
    unit: str | None = None


class Product(ApiModel):
    sku: str
    name: str
    web_name: str | None = None
    image_url: str | None = None
    product_url: str | None = None
    category: list[str] = Field(default_factory=list)
    price: ProductPrice | None = None
    ingredients: str | None = None
    dosage_form: str | None = None
    brand: str | None = None
    display_code: int | None = None
    specification: str | None = None


class LongChauSearchResult(ApiModel):
    query: str
    total_count: int = 0
    corrected_keyword: str | None = None
    searched_at: datetime | None = None
    products: list[Product] = Field(default_factory=list)


class DiseaseContext(ApiModel):
    node_id: str | None = None
    code: str | None = None
    name: str
    aliases: list[str] = Field(default_factory=list)
    description: str | None = None
    source_name: str | None = None
    source_url: str | None = None


class ConsultationNeedContext(ApiModel):
    node_id: str | None = None
    code: str | None = None
    name: str
    description: str | None = None
    long_chau_category_hints: list[str] = Field(default_factory=list)
    long_chau_category_slugs: list[str] = Field(default_factory=list)
    priority: int | None = None
    rationale: str | None = None
    evidence: str | None = None
    confidence: float | None = None
    condition_note: str | None = None
    source_name: str | None = None
    source_url: str | None = None


class WarningContext(ApiModel):
    node_id: str | None = None
    code: str | None = None
    title: str
    message: str
    warning_type: str | None = None
    severity: str | None = None
    action_text: str | None = None
    priority: int | None = None
    rationale: str | None = None
    evidence: str | None = None
    confidence: float | None = None
    trigger_note: str | None = None
    source_name: str | None = None
    source_url: str | None = None


class SourceReference(ApiModel):
    name: str = ""
    url: str = ""


class GraphContext(ApiModel):
    disease: DiseaseContext | None = None
    consultation_needs: list[ConsultationNeedContext] = Field(default_factory=list)
    warnings: list[WarningContext] = Field(default_factory=list)
    sources: list[SourceReference] = Field(default_factory=list)


class MedicationConsultationResult(ApiModel):
    status: Literal["success", "partial", "not_found", "error"]
    condition: str
    product_keyword: str
    graph: GraphContext | None = None
    products: list[Product] = Field(default_factory=list)
    product_total_count: int = 0
    corrected_keyword: str | None = None
    searched_at: datetime | None = None
    errors: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
