import httpx
import pytest

from app.medication.long_chau import LongChauClient, normalize_product


def test_normalize_product_uses_only_trusted_response_fields() -> None:
    raw = {
        "sku": "00032865",
        "name": "PARACETAMOL STADA 500MG 10X10",
        "webName": "Viên nén Paracetamol Stada 500mg",
        "image": "https://cdn.example/product.jpg",
        "category": [
            {"name": "Thuốc", "slug": "thuoc"},
            {"name": "Thuốc giảm đau", "slug": "thuoc/giam-dau"},
        ],
        "price": {
            "price": 50_000,
            "currencySymbol": "đ",
            "measureUnitName": "Hộp",
        },
        "slug": "thuoc/paracetamol-stada-500mg.html",
        "ingredients": "Paracetamol 500mg",
        "dosageForm": "Viên nén bao phim",
        "brand": "Stada",
        "displayCode": 1,
        "specification": "Hộp 10 vỉ x 10 viên",
    }

    product = normalize_product(raw, "https://nhathuoclongchau.com.vn")

    assert product.sku == "00032865"
    assert product.product_url == (
        "https://nhathuoclongchau.com.vn/thuoc/paracetamol-stada-500mg.html"
    )
    assert product.image_url == "https://cdn.example/product.jpg"
    assert product.category == ["Thuốc", "Thuốc giảm đau"]
    assert product.price.amount == 50_000
    assert product.price.currency == "đ"
    assert product.ingredients == "Paracetamol 500mg"


def test_normalize_product_does_not_invent_missing_links_or_prices() -> None:
    product = normalize_product(
        {"sku": "1", "name": "Sản phẩm thử nghiệm"},
        "https://nhathuoclongchau.com.vn",
    )

    assert product.product_url is None
    assert product.image_url is None
    assert product.price is None


def test_normalize_product_falls_back_to_prices_array_when_default_price_missing() -> None:
    raw = {
        "sku": "1",
        "name": "Sản phẩm",
        "price": {
            "price": None,
            "currencySymbol": "đ",
            "measureUnitName": "Hộp",
            "isSellDefault": True,
        },
        "prices": [
            {
                "price": None,
                "currencySymbol": "đ",
                "measureUnitName": "Viên",
                "isSellDefault": True,
                "level": 3,
            },
            {
                "price": 125_000,
                "currencySymbol": "đ",
                "measureUnitName": "Hộp",
                "isSellDefault": False,
                "level": 1,
            },
        ],
    }

    product = normalize_product(raw, "https://nhathuoclongchau.com.vn")

    assert product.price is not None
    assert product.price.amount == 125_000
    assert product.price.unit == "Hộp"


def test_normalize_product_accepts_numeric_string_price() -> None:
    product = normalize_product(
        {
            "sku": "1",
            "name": "Sản phẩm",
            "price": {
                "price": "55.000",
                "currencySymbol": "đ",
                "measureUnitName": "Hộp",
            },
        },
        "https://nhathuoclongchau.com.vn",
    )

    assert product.price is not None
    assert product.price.amount == 55_000


def test_normalize_product_returns_none_when_all_prices_are_null() -> None:
    product = normalize_product(
        {
            "sku": "1",
            "name": "Sản phẩm",
            "price": {"price": None},
            "prices": [{"price": None}],
        },
        "https://nhathuoclongchau.com.vn",
    )

    assert product.price is None


def test_normalize_product_rejects_absolute_slug_from_untrusted_payload() -> None:
    product = normalize_product(
        {"sku": "1", "name": "Sản phẩm", "slug": "https://evil.example/x"},
        "https://nhathuoclongchau.com.vn",
    )

    assert product.product_url is None


@pytest.mark.asyncio
async def test_search_normalizes_active_products_and_limits_request() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        body = request.read().decode()
        assert '"maxResultCount":8' in body
        return httpx.Response(
            200,
            json={
                "totalCount": 2,
                "correctedKeyword": "paracetamol",
                "products": [
                    {"sku": "1", "name": "A", "slug": "thuoc/a.html"},
                    {"sku": "2", "name": "B", "isActive": False},
                ],
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = LongChauClient(
        api_url="https://api.example/search",
        web_base_url="https://nhathuoclongchau.com.vn",
        timeout_seconds=10,
        client=client,
    )

    result = await adapter.search(" paracetamol ", limit=99)

    assert result.query == "paracetamol"
    assert [product.sku for product in result.products] == ["1"]


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [400, 429, 500])
async def test_search_propagates_http_errors_to_consultation_module(
    status_code: int,
) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, request=request)

    adapter = LongChauClient(
        api_url="https://api.example/search",
        web_base_url="https://nhathuoclongchau.com.vn",
        timeout_seconds=10,
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(httpx.HTTPStatusError):
        await adapter.search("đau đầu", limit=8)


@pytest.mark.asyncio
async def test_search_rejects_non_object_response() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=["unexpected"], request=request)

    adapter = LongChauClient(
        api_url="https://api.example/search",
        web_base_url="https://nhathuoclongchau.com.vn",
        timeout_seconds=10,
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(ValueError, match="invalid response"):
        await adapter.search("đau đầu", limit=8)


@pytest.mark.asyncio
async def test_get_product_recovers_price_from_detail_endpoint() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/00005809")
        return httpx.Response(
            200,
            json={
                "sku": "00005809",
                "name": "Thuốc X",
                "price": {
                    "price": 210_000,
                    "currencySymbol": "đ",
                    "measureUnitName": "Hộp",
                },
            },
        )

    adapter = LongChauClient(
        api_url="https://api.example/search",
        web_base_url="https://nhathuoclongchau.com.vn",
        timeout_seconds=10,
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    product = await adapter.get_product("00005809")

    assert product is not None
    assert product.price is not None
    assert product.price.amount == 210_000


@pytest.mark.asyncio
async def test_get_product_returns_none_on_http_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, request=request)

    adapter = LongChauClient(
        api_url="https://api.example/search",
        web_base_url="https://nhathuoclongchau.com.vn",
        timeout_seconds=10,
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    assert await adapter.get_product("00005809") is None


@pytest.mark.asyncio
async def test_search_propagates_timeout_to_consultation_module() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("upstream timed out", request=request)

    adapter = LongChauClient(
        api_url="https://api.example/search",
        web_base_url="https://nhathuoclongchau.com.vn",
        timeout_seconds=10,
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(httpx.ReadTimeout):
        await adapter.search("đau đầu", limit=8)
