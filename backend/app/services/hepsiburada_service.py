from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..integrations.hepsiburada import HepsiburadaClient
from ..integrations.hepsiburada_mapper import HepsiburadaToyMapper


class HepsiburadaService:
    """Application service for Hepsiburada product and inventory workflows."""

    def __init__(
        self,
        client: HepsiburadaClient | None = None,
        mapper: HepsiburadaToyMapper | None = None,
    ) -> None:
        self.client = client or HepsiburadaClient()
        self.mapper = mapper or HepsiburadaToyMapper()

    async def create_products(self, payload: Mapping[str, Any]) -> str:
        return await self.client.create_products(payload)

    async def list_products(self, *, merchant_sku: str | None = None) -> dict[str, Any]:
        return await self.client.list_products(merchant_sku=merchant_sku)

    async def get_categories(self) -> dict[str, Any]:
        return await self.client.get_categories()

    async def get_category_attributes(self, category_id: int) -> dict[str, Any]:
        return await self.client.get_category_attributes(category_id)

    async def update_price_and_inventory(
        self, updates: list[Mapping[str, Any]]
    ) -> str:
        if not updates:
            raise ValueError("at least one Hepsiburada inventory update is required")
        items: list[dict[str, Any]] = []
        for update in updates:
            merchant_sku = str(update.get("merchantSku", update.get("merchant_sku", "")))
            quantity = update.get("quantity")
            price = update.get("price", update.get("salePrice", update.get("sale_price")))
            if not merchant_sku:
                raise ValueError("merchantSku is required")
            if quantity is None or isinstance(quantity, bool) or int(quantity) < 0:
                raise ValueError("quantity must be a non-negative integer")
            if price is None or float(price) <= 0:
                raise ValueError("price must be greater than zero")
            items.append({"merchantSku": merchant_sku, "quantity": int(quantity), "price": float(price)})
        return await self.client.update_price_and_inventory({"items": items})

    def map_toy_attributes(
        self,
        *,
        category_id: str,
        product: Mapping[str, Any],
        extra_attributes: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.mapper.map_product_attributes(
            category_id=category_id,
            product=product,
            extra_attributes=extra_attributes,
        )

    async def close(self) -> None:
        await self.client.close()

    async def __aenter__(self) -> HepsiburadaService:
        return self

    async def __aexit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        await self.close()