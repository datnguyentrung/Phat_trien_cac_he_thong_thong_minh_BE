import pytest

from app.medication.models import (
    GraphContext,
    LongChauSearchResult,
    Product,
    ProductPrice,
)
from app.medication.service import MedicationConsultationService


class StubGraphRepository:
    def __init__(self, result=None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error

    async def find_consultation_context(self, condition: str):
        if self.error:
            raise self.error
        return self.result


class StubProductSearch:
    def __init__(self, result=None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error

    async def search(self, keyword: str, limit: int):
        if self.error:
            raise self.error
        return self.result


class StubProductSearchWithDetail(StubProductSearch):
    def __init__(
        self,
        result=None,
        detail: Product | None = None,
        detail_error: Exception | None = None,
    ) -> None:
        super().__init__(result)
        self.detail = detail
        self.detail_error = detail_error

    async def get_product(self, sku: str):
        if self.detail_error:
            raise self.detail_error
        return self.detail


@pytest.mark.asyncio
async def test_consultation_success_combines_graph_and_products() -> None:
    graph = GraphContext(disease={"name": "Đau nửa đầu"})
    products = LongChauSearchResult(
        query="thuốc đau đầu",
        total_count=1,
        products=[Product(sku="1", name="Sản phẩm A")],
    )
    service = MedicationConsultationService(
        graph_repository=StubGraphRepository(graph),
        product_search=StubProductSearch(products),
    )

    result = await service.consult("đau nửa đầu", "thuốc đau đầu")

    assert result.status == "success"
    assert result.graph == graph
    assert result.products == products.products
    assert result.errors == []


@pytest.mark.asyncio
async def test_consultation_is_partial_when_graph_is_unavailable() -> None:
    products = LongChauSearchResult(
        query="thuốc đau đầu",
        total_count=1,
        products=[Product(sku="1", name="Sản phẩm A")],
    )
    service = MedicationConsultationService(
        graph_repository=StubGraphRepository(error=RuntimeError("secret database URL")),
        product_search=StubProductSearch(products),
    )

    result = await service.consult("đau đầu", "thuốc đau đầu")

    assert result.status == "partial"
    assert result.products
    assert result.graph is None
    assert result.errors == ["knowledge_graph_unavailable"]
    assert "secret" not in result.model_dump_json()
    assert any("Không xếp hạng" in item for item in result.limitations)


@pytest.mark.asyncio
async def test_consultation_errors_when_both_sources_are_unavailable() -> None:
    service = MedicationConsultationService(
        graph_repository=StubGraphRepository(error=RuntimeError("db failed")),
        product_search=StubProductSearch(error=RuntimeError("http failed")),
    )

    result = await service.consult("đau đầu", "thuốc đau đầu")

    assert result.status == "error"
    assert result.errors == [
        "knowledge_graph_unavailable",
        "product_search_unavailable",
    ]


@pytest.mark.asyncio
async def test_consultation_enriches_missing_price_from_product_detail() -> None:
    graph = GraphContext(disease={"name": "Đau đầu"})
    search_result = LongChauSearchResult(
        query="thuốc đau đầu",
        total_count=1,
        products=[Product(sku="1", name="Sản phẩm A")],
    )
    detail = Product(
        sku="1",
        name="Sản phẩm A",
        price=ProductPrice(amount=55_000, currency="đ", unit="Hộp"),
    )
    service = MedicationConsultationService(
        graph_repository=StubGraphRepository(graph),
        product_search=StubProductSearchWithDetail(search_result, detail=detail),
    )

    result = await service.consult("đau đầu", "thuốc đau đầu")

    assert result.status == "success"
    assert result.products[0].price is not None
    assert result.products[0].price.amount == 55_000


@pytest.mark.asyncio
async def test_consultation_keeps_missing_price_when_detail_fails() -> None:
    graph = GraphContext(disease={"name": "Đau đầu"})
    search_result = LongChauSearchResult(
        query="thuốc đau đầu",
        total_count=1,
        products=[Product(sku="1", name="Sản phẩm A")],
    )
    service = MedicationConsultationService(
        graph_repository=StubGraphRepository(graph),
        product_search=StubProductSearchWithDetail(
            search_result,
            detail_error=RuntimeError("detail failed"),
        ),
    )

    result = await service.consult("đau đầu", "thuốc đau đầu")

    assert result.status == "success"
    assert result.products[0].price is None
