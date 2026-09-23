from __future__ import annotations

import base64

import httpx
import pytest

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
            {"name": "CE Uygunluk", "value": "Evet"},
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
