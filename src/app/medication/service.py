import asyncio

from app.chat.progress import push_progress
from app.medication.models import (
    GraphContext,
    LongChauSearchResult,
    MedicationConsultationResult,
    Product,
    ProductPrice,
)
from app.medication.ports import MedicationGraphRepository, ProductSearch


class MedicationConsultationService:
    def __init__(
        self,
        graph_repository: MedicationGraphRepository,
        product_search: ProductSearch,
        search_limit: int = 8,
        summary_limit: int = 4,
    ) -> None:
        self._graph_repository = graph_repository
        self._product_search = product_search
        self._search_limit = max(1, min(search_limit, 8))
        self._summary_limit = max(1, min(summary_limit, 4))

    async def consult(
        self,
        condition: str,
        product_keyword: str,
    ) -> MedicationConsultationResult:
        push_progress("Đang tra cứu Knowledge Graph...", 20)
        push_progress(
            "Đang tìm kiếm sản phẩm tham khảo trên Long Châu...",
            30,
        )
        graph_value, product_value = await asyncio.gather(
            self._graph_repository.find_consultation_context(condition),
            self._product_search.search(product_keyword, limit=self._search_limit),
            return_exceptions=True,
        )

        errors: list[str] = []
        graph: GraphContext | None = None
        product_result: LongChauSearchResult | None = None
        if isinstance(graph_value, BaseException):
            errors.append("knowledge_graph_unavailable")
        else:
            graph = graph_value
        if isinstance(product_value, BaseException):
            errors.append("product_search_unavailable")
        else:
            product_result = product_value

        products = product_result.products[: self._summary_limit] if product_result else []
        push_progress("Đang lọc và sắp xếp sản phẩm...", 40)
        products = await self._enrich_product_prices(products)
        push_progress("Đang đối chiếu cảnh báo an toàn...", 50)
        has_data = graph is not None or bool(products)
        if len(errors) == 2:
            status = "error"
        elif errors:
            status = "partial"
        elif has_data:
            status = "success"
        else:
            status = "not_found"

        limitations = [
            "Kết quả sản phẩm chỉ để tham khảo, không phải đơn thuốc.",
            "Không tự thay đổi thuốc hoặc liều dùng nếu chưa hỏi bác sĩ/dược sĩ.",
        ]
        if "knowledge_graph_unavailable" in errors:
            limitations.append(
                "Knowledge Graph tạm thời không khả dụng nên chưa thể đối chiếu cảnh báo theo bệnh."
            )
            limitations.append(
                "Không xếp hạng mức độ phù hợp của sản phẩm khi thiếu dữ liệu cảnh báo từ Knowledge Graph."
            )

        return MedicationConsultationResult(
            status=status,
            condition=condition.strip(),
            product_keyword=product_keyword.strip(),
            graph=graph,
            products=products,
            product_total_count=product_result.total_count if product_result else 0,
            corrected_keyword=(
                product_result.corrected_keyword if product_result else None
            ),
            searched_at=product_result.searched_at if product_result else None,
            errors=errors,
            limitations=limitations,
        )

    async def _enrich_product_prices(
        self,
        products: list[Product],
    ) -> list[Product]:
        """Recover missing prices from the Long Châu product detail endpoint."""
        get_product = getattr(self._product_search, "get_product", None)
        missing = [product for product in products if product.price is None]
        if get_product is None or not missing:
            return products
        values = await asyncio.gather(
            *(get_product(product.sku) for product in missing),
            return_exceptions=True,
        )
        prices_by_sku: dict[str, ProductPrice] = {}
        for product, value in zip(missing, values, strict=True):
            if isinstance(value, BaseException) or value is None:
                continue
            if value.price is not None:
                prices_by_sku[product.sku] = value.price
        if not prices_by_sku:
            return products
        return [
            (
                product.model_copy(update={"price": prices_by_sku[product.sku]})
                if product.sku in prices_by_sku
                else product
            )
            for product in products
        ]
