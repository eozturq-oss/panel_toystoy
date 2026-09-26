from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.hepsiburada import get_hepsiburada_service, router
from app.main import app as main_app


class FakeHepsiburadaService:
    def __init__(self) -> None:
        self.requested_sku: str | None = None
        self.inventory_updates: list[dict[str, Any]] = []

    async def list_products(self, *, merchant_sku: str | None = None) -> dict[str, Any]:
        self.requested_sku = merchant_sku
        return {"products": [{"merchantSku": merchant_sku or "SKU-1"}]}

    async def create_products(self, payload: dict[str, Any]) -> str:
        return "create-batch-1"

    async def update_price_and_inventory(self, updates: list[dict[str, Any]]) -> str:
        self.inventory_updates = updates
        return "inventory-batch-1"

    async def get_categories(self) -> dict[str, Any]:
        return {"categories": []}

    async def get_category_attributes(self, category_id: int) -> dict[str, Any]:
        return {"categoryId": category_id, "attributes": []}

    def map_toy_attributes(self, **kwargs: Any) -> dict[str, Any]:
        return {"categoryId": kwargs["category_id"], "attributes": []}

    async def close(self) -> None:
        return None


def test_hepsiburada_routes_are_documented_and_connected_to_service() -> None:
    service = FakeHepsiburadaService()
    api = FastAPI()
    api.include_router(router)
    api.dependency_overrides[get_hepsiburada_service] = lambda: service

    assert "/api/v1/hepsiburada/products" in main_app.openapi()["paths"]
    with TestClient(api) as client:
        listed = client.get("/api/v1/hepsiburada/products", params={"merchant_sku": "SKU-1"})
        updated = client.put(
            "/api/v1/hepsiburada/inventory",
            json={"items": [{"merchantSku": "SKU-1", "quantity": 4, "price": 129.9}]},
        )
        mapped = client.post(
            "/api/v1/hepsiburada/toy-attributes",
            json={
                "category_id": "TOY-CONSTRUCTION",
                "age_group": "3-6 Yaş",
                "gender": "Unisex",
                "ce_compliant": True,
                "piece_count": 60,
                "material": "ABS Plastik",
            },
        )

    assert listed.status_code == 200
    assert service.requested_sku == "SKU-1"
    assert updated.status_code == 202
    assert service.inventory_updates == [
        {"merchantSku": "SKU-1", "quantity": 4, "price": Decimal("129.9")}
    ]
    assert mapped.json() == {"categoryId": "TOY-CONSTRUCTION", "attributes": []}