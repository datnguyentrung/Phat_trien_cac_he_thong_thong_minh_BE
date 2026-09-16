from datetime import UTC, datetime
from typing import Any
from urllib.parse import urljoin, urlsplit

import httpx

from app.medication.models import LongChauSearchResult, Product, ProductPrice


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _price_amount(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip().replace(".", "").replace(",", "")
        if cleaned.isdigit():
            return float(cleaned)
    return None


def _extract_price(raw: dict[str, Any]) -> ProductPrice | None:
    """Best-effort price extraction from Long Châu price fields."""
    candidates: list[dict[str, Any]] = []
    price_data = raw.get("price")
    if isinstance(price_data, dict):
        candidates.append(price_data)
    price_list = raw.get("prices")
    if isinstance(price_list, list):
        candidates.extend(item for item in price_list if isinstance(item, dict))

    ordered = sorted(
        candidates,
        key=lambda item: (
            not bool(item.get("isSellDefault")),
            not bool(item.get("isDefault")),
            item.get("level") if isinstance(item.get("level"), int) else 99,
        ),
    )
    for candidate in ordered:
        amount = _price_amount(candidate.get("price"))
        if amount is not None:
            return ProductPrice(
                amount=amount,
                currency=_optional_text(candidate.get("currencySymbol")),
                unit=_optional_text(candidate.get("measureUnitName")),
            )
    return None


def _trusted_product_url(slug: str | None, web_base_url: str) -> str | None:
    if not slug:
        return None
    parsed = urlsplit(slug)
    if parsed.scheme or parsed.netloc:
        return None
    clean_path = parsed.path.lstrip("/")
    return urljoin(f"{web_base_url.rstrip('/')}/", clean_path) if clean_path else None


def normalize_product(raw: dict[str, Any], web_base_url: str) -> Product:
    """Normalize one Long Châu search record without inferring medical claims."""
    price = _extract_price(raw)

    category_data = raw.get("category")
    categories = []
    if isinstance(category_data, list):
        categories = [
            name
            for item in category_data
            if isinstance(item, dict)
            and (name := _optional_text(item.get("name"))) is not None
        ]

    slug = _optional_text(raw.get("slug"))
    product_url = _trusted_product_url(slug, web_base_url)

    return Product(
        sku=_optional_text(raw.get("sku")) or "unknown",
        name=_optional_text(raw.get("name")) or "Sản phẩm chưa có tên",
        web_name=_optional_text(raw.get("webName")),
        image_url=_optional_text(raw.get("image")),
        product_url=product_url,
        category=categories,
        price=price,
        ingredients=_optional_text(raw.get("ingredients")),
        dosage_form=_optional_text(raw.get("dosageForm")),
        brand=_optional_text(raw.get("brand")),
        display_code=(
            raw.get("displayCode")
            if isinstance(raw.get("displayCode"), int)
            else None
        ),
        specification=_optional_text(raw.get("specification")),
    )


class LongChauClient:
    def __init__(
        self,
        api_url: str,
        web_base_url: str,
        timeout_seconds: float,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_url = api_url
        self._web_base_url = web_base_url
        self._timeout = timeout_seconds
        self._client = client
        self._owns_client = client is None

    async def search(self, keyword: str, limit: int) -> LongChauSearchResult:
        clean_keyword = keyword.strip()[:200]
        clean_limit = max(1, min(limit, 8))
        if not clean_keyword:
            return LongChauSearchResult(query=clean_keyword)

        client = self._client
        if client is None:
            client = httpx.AsyncClient(timeout=self._timeout)
            self._client = client

        response = await client.post(
            self._api_url,
            headers={"accept": "application/json", "Content-Type": "application/json"},
            json={
                "isAutoCorrect": True,
                "skipCount": 0,
                "maxResultCount": clean_limit,
                "codes": [],
                "sortType": 4,
                "keyword": clean_keyword,
                "category": [],
            },
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Long Châu returned an invalid response")

        raw_products = payload.get("products")
        if not isinstance(raw_products, list):
            raw_products = []
        products = [
            normalize_product(item, self._web_base_url)
            for item in raw_products[:clean_limit]
            if isinstance(item, dict)
            and item.get("isActive", True) is not False
            and item.get("isPublish", True) is not False
        ]
        total_count = payload.get("totalCount", len(products))

        return LongChauSearchResult(
            query=clean_keyword,
            total_count=total_count if isinstance(total_count, int) else len(products),
            corrected_keyword=_optional_text(payload.get("correctedKeyword")),
            searched_at=datetime.now(UTC),
            products=products,
        )

    async def get_product(self, sku: str) -> Product | None:
        """Fetch one product by SKU to recover a price missing from search."""
        clean_sku = (sku or "").strip()
        if not clean_sku:
            return None
        client = self._client
        if client is None:
            client = httpx.AsyncClient(timeout=self._timeout)
            self._client = client
        prefix = self._api_url.rsplit("/", 1)[0]
        try:
            response = await client.get(
                f"{prefix}/{clean_sku}",
                headers={"accept": "application/json"},
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError):
            return None
        if not isinstance(payload, dict) or payload.get("sku") != clean_sku:
            return None
        return normalize_product(payload, self._web_base_url)

    async def close(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None
