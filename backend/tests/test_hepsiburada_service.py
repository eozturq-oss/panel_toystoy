from __future__ import annotations

import asyncio

from app.services.hepsiburada_service import HepsiburadaService


class FakeHepsiburadaClient:
    def __init__(self) -> None:
        self.payload = None
        self.merchant_sku = None

    async def create_products(self, payload):
        return "create-1"

    async def list_products(self, *, merchant_sku=None):
        self.merchant_sku = merchant_sku
        return {"products": [{"merchantSku": merchant_sku or "SKU-1"}]}

    async def update_price_and_inventory(self, payload):
        self.payload = payload
        return "inventory-1"

    async def close(self):
        return None


def test_hepsiburada_service_formats_inventory_and_toy_attributes() -> None:
    client = FakeHepsiburadaClient()
    service = HepsiburadaService(client=client)

    batch_id = asyncio.run(service.update_price_and_inventory([
        {"merchant_sku": "TOY-1", "quantity": 4, "sale_price": "129.90"},
    ]))
    mapped = service.map_toy_attributes(
        category_id="TOY-CONSTRUCTION",
        product={
            "age_group": "3-6 Yaş",
            "gender": "Unisex",
            "ce_compliant": True,
            "piece_count": 60,
            "material": "ABS Plastik",
            "safety_warning": "Küçük parça içerir.",
        },
    )

    assert batch_id == "inventory-1"
    assert client.payload == {
        "items": [{"merchantSku": "TOY-1", "quantity": 4, "price": 129.9}]
    }
    assert {item["name"] for item in mapped["attributes"]} >= {"Uyarı Metni"}


def test_hepsiburada_service_lists_products_by_merchant_sku() -> None:
    client = FakeHepsiburadaClient()
    service = HepsiburadaService(client=client)

    result = asyncio.run(service.list_products(merchant_sku="SKU-1"))

    assert result == {"products": [{"merchantSku": "SKU-1"}]}
    assert client.merchant_sku == "SKU-1"
