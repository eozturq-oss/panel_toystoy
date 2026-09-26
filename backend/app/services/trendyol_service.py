from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..integrations.trendyol import TrendyolClient
from ..integrations.trendyol_inventory import format_bulk_inventory_update
from ..integrations.trendyol_mapper import TrendyolCategoryMapper


class TrendyolService:
    """Application service for toy-specific Trendyol operations."""

    def __init__(
        self,
        client: TrendyolClient | None = None,
        mapper: TrendyolCategoryMapper | None = None,
    ) -> None:
        self.client = client or TrendyolClient()
        self.mapper = mapper or TrendyolCategoryMapper()

    async def get_products(
        self,
        *,
        page: int = 0,
        size: int = 50,
        approved: bool | None = None,
        barcode: str | None = None,
    ) -> dict[str, Any]:
        return await self.client.get_products(
            page=page, size=size, approved=approved, barcode=barcode
        )

    async def update_price_and_inventory(
        self, updates: list[Mapping[str, Any]]
    ) -> str:
        payload = format_bulk_inventory_update(updates)
        return await self.client.update_price_and_inventory(payload)

    async def map_toy_category(
        self,
        *,
        local_category: str,
        product_attributes: Mapping[str, Any],
        category_aliases: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        category_response = await self.client.get_categories()
        category = self.mapper if category_aliases is None else TrendyolCategoryMapper(
            category_aliases=category_aliases
        )
        category_match = category._find_category(local_category, category_response)
        category_id = category_match.get("id", category_match.get("categoryId"))
        if category_id is None:
            raise ValueError(f"Trendyol category not found for '{local_category}'")
        attribute_response = await self.client.get_category_attributes(int(category_id))
        return category.map_toy_category(
            local_category=local_category,
            category_response=category_response,
            attribute_response=attribute_response,
            product_attributes=product_attributes,
        )

    async def close(self) -> None:
        await self.client.close()

    async def __aenter__(self) -> TrendyolService:
        return self

    async def __aexit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        await self.close()