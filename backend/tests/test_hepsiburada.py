from __future__ import annotations

import base64

import httpx
import pytest
from pydantic import SecretStr

from app.config import Settings
from app.integrations.hepsiburada import HepsiburadaClient
from app.integrations.hepsiburada_mapper import (
    HepsiburadaMappingError,
    map_toy_attributes,
)


def settings() -> Settings:
    return Settings(
        trendyol_supplier_id="123456",
        trendyol_api_key="api-key",
        trendyol_api_secret="api-secret",
        hepsiburada_merchant_id="merchant-1",
        hepsiburada_username="hb-user",
        hepsiburada_password="hb-secret",
        hepsiburada_base_url="https://example.test",
    )


@pytest.mark.asyncio
async def test_hepsiburada_bulk_inventory_uses_basic_auth_and_merchant_path() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["authorization"] = request.headers["Authorization"]
        return httpx.Response(200, json={"batchId": "hb-batch-1"})

    client = HepsiburadaClient(settings())
    await client._client.aclose()
    client._client = httpx.AsyncClient(
        base_url="https://example.test",
        transport=httpx.MockTransport(handler),
        auth=("hb-user", "hb-secret"),
    )

    batch_id = await client.update_price_and_inventory(
        {"items": [{"merchantSku": "SKU-1", "quantity": 3, "salePrice": 129.9}]}
    )
    await client.close()

    assert batch_id == "hb-batch-1"
    assert captured["path"] == "/listings/merchantid/merchant-1/inventory-uploads"
    assert captured["authorization"] == "Basic " + base64.b64encode(b"hb-user:hb-secret").decode()


@pytest.mark.asyncio
async def test_list_products_filters_by_merchant_sku() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["merchant_sku"] = request.url.params["merchantSku"]
        return httpx.Response(200, json={"products": [{"merchantSku": "SKU-1"}]})

    client = HepsiburadaClient(settings())
    await client._client.aclose()
    client._client = httpx.AsyncClient(
        base_url="https://example.test",
        transport=httpx.MockTransport(handler),
    )

    result = await client.list_products(merchant_sku="SKU-1")
    await client.close()

    assert result["products"] == [{"merchantSku": "SKU-1"}]
    assert captured == {
        "path": "/listings/merchantid/merchant-1/products",
        "merchant_sku": "SKU-1",
    }


@pytest.mark.asyncio
async def test_secret_key_and_merchant_id_can_supply_basic_auth() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["authorization"] = request.headers["Authorization"]
        return httpx.Response(200, json={"products": []})

    config = settings().model_copy(
        update={
            "hepsiburada_username": None,
            "hepsiburada_password": None,
            "hepsiburada_secret_key": SecretStr("hb-key"),
        }
    )
    client = HepsiburadaClient(config)
    auth = client._client._auth
    await client._client.aclose()
    client._client = httpx.AsyncClient(
        base_url="https://example.test",
        transport=httpx.MockTransport(handler),
        auth=auth,
    )

    await client.list_products()
    await client.close()

    assert captured["authorization"] == "Basic " + base64.b64encode(
        b"merchant-1:hb-key"
    ).decode()


def test_maps_required_toy_attributes_to_hepsiburada_name_value_format() -> None:
    result = map_toy_attributes(
        category_id="TOY-CONSTRUCTION",
        age_group="3-6 Yaş",
        gender="Unisex",
        ce_compliant=True,
        piece_count=60,
        material="ABS Plastik",
    )

    assert result == {
        "categoryId": "TOY-CONSTRUCTION",
        "attributes": [
            {"name": "Yaş Grubu", "value": "3-6 Yaş"},
            {"name": "Cinsiyet", "value": "Unisex"},
            {"name": "CE Sertifika Bilgisi", "value": "Evet"},
            {"name": "Parça Sayısı", "value": "60"},
            {"name": "Materyal", "value": "ABS Plastik"},
        ],
    }


def test_mapper_rejects_missing_required_toy_attribute() -> None:
    from app.integrations.hepsiburada_mapper import HepsiburadaToyMapper

    with pytest.raises(HepsiburadaMappingError):
        HepsiburadaToyMapper().map_product_attributes(
            category_id="TOY-CONSTRUCTION",
            product={"age_group": "3-6 Yaş"},
        )
