from __future__ import annotations

import base64

import httpx
import pytest

from app.config import Settings
from app.integrations.trendyol import TrendyolClient


@pytest.mark.asyncio
async def test_get_products_sends_basic_auth_and_supplier_endpoint() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers["Authorization"]
        captured["user_agent"] = request.headers["User-Agent"]
        return httpx.Response(200, json={"content": [], "totalElements": 0})

    settings = Settings(
        trendyol_supplier_id="123456",
        trendyol_api_key="api-key",
        trendyol_api_secret="api-secret",
        trendyol_base_url="https://example.test",
        trendyol_user_agent="test-client",
    )
    client = TrendyolClient(settings)
    await client._client.aclose()
    client._client = httpx.AsyncClient(
        base_url=settings.trendyol_base_url,
        transport=httpx.MockTransport(handler),
        auth=(settings.trendyol_api_key.get_secret_value(), settings.trendyol_api_secret.get_secret_value()),
        headers={"User-Agent": settings.trendyol_user_agent},
    )

    result = await client.get_products(page=2, size=25, approved=True)
    await client.close()

    expected_auth = base64.b64encode(b"api-key:api-secret").decode()
    assert result["totalElements"] == 0
    assert captured["url"] == "https://example.test/suppliers/123456/v2/products?page=2&size=25&approved=true"
    assert captured["authorization"] == f"Basic {expected_auth}"
    assert captured["user_agent"] == "test-client"


@pytest.mark.asyncio
async def test_create_products_returns_batch_request_id() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["payload"] = request.read().decode()
        return httpx.Response(200, json={"batchRequestId": "batch-123"})

    settings = Settings(
        trendyol_supplier_id="123456",
        trendyol_api_key="api-key",
        trendyol_api_secret="api-secret",
        trendyol_base_url="https://example.test",
    )
    client = TrendyolClient(settings)
    await client._client.aclose()
    client._client = httpx.AsyncClient(
        base_url=settings.trendyol_base_url,
        transport=httpx.MockTransport(handler),
    )

    batch_id = await client.create_products({"items": [{"barcode": "8690000000001"}]})
    await client.close()

    assert batch_id == "batch-123"
    assert captured["path"] == "/suppliers/123456/v2/products"
    assert '"barcode":"8690000000001"' in str(captured["payload"])


@pytest.mark.asyncio
async def test_get_batch_status_uses_batch_request_endpoint() -> None:
    requested_path = ""

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requested_path
        requested_path = request.url.path
        return httpx.Response(200, json={"status": "COMPLETED"})

    settings = Settings(
        trendyol_supplier_id="123456",
        trendyol_api_key="api-key",
        trendyol_api_secret="api-secret",
        trendyol_base_url="https://example.test",
    )
    client = TrendyolClient(settings)
    await client._client.aclose()
    client._client = httpx.AsyncClient(
        base_url=settings.trendyol_base_url,
        transport=httpx.MockTransport(handler),
    )

    result = await client.get_batch_status("batch-123")
    await client.close()

    assert result == {"status": "COMPLETED"}
    assert requested_path == "/suppliers/123456/products/batch-requests/batch-123"


@pytest.mark.asyncio
async def test_update_price_and_inventory_posts_lightweight_bulk_payload() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["payload"] = request.read().decode()
        return httpx.Response(200, json={"batchRequestId": "inventory-batch-1"})

    settings = Settings(
        trendyol_supplier_id="123456",
        trendyol_api_key="api-key",
        trendyol_api_secret="api-secret",
        trendyol_base_url="https://example.test",
    )
    client = TrendyolClient(settings)
    await client._client.aclose()
    client._client = httpx.AsyncClient(
        base_url=settings.trendyol_base_url,
        transport=httpx.MockTransport(handler),
    )

    batch_id = await client.update_price_and_inventory(
        {
            "items": [
                {"barcode": "8690000000001", "quantity": 10, "salePrice": 249.9},
                {"barcode": "8690000000002", "quantity": 0, "salePrice": 99.9},
            ]
        }
    )
    await client.close()

    assert batch_id == "inventory-batch-1"
    assert captured["path"] == "/suppliers/123456/products/price-and-inventory"
    assert '"quantity":10' in str(captured["payload"])
    assert '"salePrice":249.9' in str(captured["payload"])
