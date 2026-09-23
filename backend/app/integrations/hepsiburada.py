from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx

from ..config import Settings, get_settings
from .base import MarketplaceClient


class HepsiburadaApiError(RuntimeError):
    """Raised when Hepsiburada returns an unsuccessful API response."""


class HepsiburadaClient(MarketplaceClient):
    """Hepsiburada Listing API adapter using merchant Basic Auth."""

    products_path = "/listings/merchantid/{merchant_id}/products"
    inventory_path = "/listings/merchantid/{merchant_id}/inventory-uploads"
    categories_path = "/product/api/categories"
    category_attributes_path = "/product/api/categories/{category_id}/attributes"
    orders_path = "/oms/orders"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        missing = (
            "hepsiburada_merchant_id",
            "hepsiburada_username",
            "hepsiburada_password",
        )
        if any(getattr(self.settings, name) in (None, "") for name in missing):
            raise ValueError("Hepsiburada merchant ID, username and password are required")

        self._client = httpx.AsyncClient(
            base_url=self.settings.hepsiburada_base_url.rstrip("/"),
            auth=(
                self.settings.hepsiburada_username or "",
                (self.settings.hepsiburada_password or "").get_secret_value(),
            ),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=self.settings.hepsiburada_timeout_seconds,
        )

    async def create_products(self, payload: Mapping[str, Any]) -> str:
        if self.settings.marketplace_dry_run:
            return "dry-run-hepsiburada-create"
        response = await self._post_json(
            self.products_path.format(merchant_id=self.settings.hepsiburada_merchant_id),
            payload,
            resource_name="create products",
        )
        return self._batch_id(response)

    async def update_price_and_inventory(self, payload: Mapping[str, Any]) -> str:
        if self.settings.marketplace_dry_run:
            return "dry-run-hepsiburada-inventory"
        response = await self._post_json(
            self.inventory_path.format(merchant_id=self.settings.hepsiburada_merchant_id),
            payload,
            resource_name="price and inventory update",
        )
        return self._batch_id(response)

    async def get_categories(self) -> dict[str, Any]:
        return await self._get_json(self.categories_path, resource_name="categories")

    async def get_category_attributes(self, category_id: int) -> dict[str, Any]:
        if category_id <= 0:
            raise ValueError("category_id must be greater than zero")
        return await self._get_json(
            self.category_attributes_path.format(category_id=category_id),
            resource_name=f"category attributes for {category_id}",
        )

    async def fetch_orders(self, *, since: str | None = None) -> list[dict[str, Any]]:
        params: dict[str, str] = {"pageSize": "200"}
        if since:
            params["lastModifiedDate"] = since
        response = await self._get_json(self.orders_path, resource_name="orders", params=params)
        orders = response.get("orders", response.get("content", []))
        return [order for order in orders if isinstance(order, dict)] if isinstance(orders, list) else []

    async def _get_json(
        self,
        path: str,
        *,
        resource_name: str,
        params: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        response = await self._client.get(path, params=params)
        return self._parse_response(response, resource_name)

    async def _post_json(
        self, path: str, payload: Mapping[str, Any], *, resource_name: str
    ) -> dict[str, Any]:
        response = await self._client.post(path, json=dict(payload))
        return self._parse_response(response, resource_name)

    def _parse_response(self, response: httpx.Response, resource_name: str) -> dict[str, Any]:
        if response.is_error:
            raise HepsiburadaApiError(
                f"Hepsiburada {resource_name} request failed with HTTP "
                f"{response.status_code}: {response.text[:500]}"
            )
        payload = response.json()
        if not isinstance(payload, dict):
            raise HepsiburadaApiError(f"Hepsiburada {resource_name} response must be a JSON object")
        return payload

    @staticmethod
    def _batch_id(response: Mapping[str, Any]) -> str:
        batch_id = response.get("batchRequestId") or response.get("batchId") or response.get("id")
        if not batch_id:
            raise HepsiburadaApiError("Hepsiburada response has no batch identifier")
        return str(batch_id)

    async def close(self) -> None:
        await self._client.aclose()
