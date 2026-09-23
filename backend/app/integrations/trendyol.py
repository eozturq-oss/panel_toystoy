from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx

from ..config import Settings, get_settings
from .base import MarketplaceClient


class TrendyolApiError(RuntimeError):
    """Raised when Trendyol returns an unsuccessful API response."""


class TrendyolClient(MarketplaceClient):
    products_path = "/suppliers/{supplier_id}/v2/products"
    categories_path = "/suppliers/{supplier_id}/v2/categories"
    category_attributes_path = "/suppliers/{supplier_id}/v2/product-categories/{category_id}/attributes"
    batch_status_path = "/suppliers/{supplier_id}/products/batch-requests/{batch_request_id}"
    price_inventory_path = "/suppliers/{supplier_id}/products/price-and-inventory"
    orders_path = "/suppliers/{supplier_id}/orders"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._client = httpx.AsyncClient(
            base_url=self.settings.trendyol_base_url.rstrip("/"),
            auth=(
                self.settings.trendyol_api_key.get_secret_value(),
                self.settings.trendyol_api_secret.get_secret_value(),
            ),
            headers={
                "Accept": "application/json",
                "User-Agent": self.settings.trendyol_user_agent,
            },
            timeout=self.settings.trendyol_timeout_seconds,
        )

    async def get_products(
        self,
        *,
        page: int = 0,
        size: int = 50,
        approved: bool | None = None,
        barcode: str | None = None,
    ) -> dict[str, Any]:
        """Fetch products from the Trendyol Supplier API."""
        if page < 0:
            raise ValueError("page must be greater than or equal to zero")
        if not 1 <= size <= 2_000:
            raise ValueError("size must be between 1 and 2000")

        params: dict[str, str | int | bool] = {"page": page, "size": size}
        if approved is not None:
            params["approved"] = approved
        if barcode:
            params["barcode"] = barcode

        return await self._get_json(
            self.products_path.format(supplier_id=self.settings.trendyol_supplier_id),
            params=params,
            resource_name="products",
        )

    async def get_categories(self) -> dict[str, Any]:
        """Fetch the Trendyol category tree for the configured supplier."""
        return await self._get_json(
            self.categories_path.format(supplier_id=self.settings.trendyol_supplier_id),
            resource_name="categories",
        )

    async def get_category_attributes(self, category_id: int) -> dict[str, Any]:
        """Fetch attribute definitions and allowed values for a Trendyol category."""
        if category_id <= 0:
            raise ValueError("category_id must be greater than zero")
        return await self._get_json(
            self.category_attributes_path.format(
                supplier_id=self.settings.trendyol_supplier_id,
                category_id=category_id,
            ),
            resource_name=f"category attributes for {category_id}",
        )

    async def create_products(self, payload: Mapping[str, Any]) -> str:
        """Submit products to Trendyol and return the asynchronous batch ID."""
        if self.settings.marketplace_dry_run:
            return "dry-run-trendyol-create"
        response_payload = await self._post_json(
            self.products_path.format(supplier_id=self.settings.trendyol_supplier_id),
            payload,
            resource_name="create products",
        )
        batch_request_id = response_payload.get("batchRequestId")
        if not batch_request_id:
            raise TrendyolApiError("Trendyol create products response has no batchRequestId")
        return str(batch_request_id)

    async def get_batch_status(self, batch_request_id: str) -> dict[str, Any]:
        """Fetch the processing result of an asynchronous product batch."""
        if not batch_request_id.strip():
            raise ValueError("batch_request_id cannot be empty")
        return await self._get_json(
            self.batch_status_path.format(
                supplier_id=self.settings.trendyol_supplier_id,
                batch_request_id=batch_request_id,
            ),
            resource_name=f"batch status for {batch_request_id}",
        )

    async def update_price_and_inventory(self, payload: Mapping[str, Any]) -> str:
        """Send one or more lightweight stock and price updates."""
        if self.settings.marketplace_dry_run:
            return "dry-run-trendyol-inventory"
        response_payload = await self._post_json(
            self.price_inventory_path.format(supplier_id=self.settings.trendyol_supplier_id),
            payload,
            resource_name="price and inventory update",
        )
        batch_request_id = response_payload.get("batchRequestId")
        if not batch_request_id:
            raise TrendyolApiError(
                "Trendyol price and inventory response has no batchRequestId"
            )
        return str(batch_request_id)

    async def fetch_orders(self, *, since: str | None = None) -> list[dict[str, Any]]:
        params: dict[str, str] = {"size": "200"}
        if since:
            params["startDate"] = since
        response = await self._get_json(
            self.orders_path.format(supplier_id=self.settings.trendyol_supplier_id),
            params=params,
            resource_name="orders",
        )
        orders = response.get("content", response.get("orders", []))
        return [order for order in orders if isinstance(order, dict)] if isinstance(orders, list) else []

    async def _get_json(
        self,
        path: str,
        *,
        resource_name: str,
        params: dict[str, str | int | bool] | None = None,
    ) -> dict[str, Any]:
        response = await self._client.get(path, params=params)
        if response.is_error:
            raise TrendyolApiError(
                f"Trendyol {resource_name} request failed with HTTP "
                f"{response.status_code}: {response.text[:500]}"
            )
        payload = response.json()
        if not isinstance(payload, dict):
            raise TrendyolApiError(f"Trendyol {resource_name} response must be a JSON object")
        return payload

    async def _post_json(
        self,
        path: str,
        payload: Mapping[str, Any],
        *,
        resource_name: str,
    ) -> dict[str, Any]:
        response = await self._client.post(path, json=dict(payload))
        if response.is_error:
            raise TrendyolApiError(
                f"Trendyol {resource_name} request failed with HTTP "
                f"{response.status_code}: {response.text[:500]}"
            )
        response_payload = response.json()
        if not isinstance(response_payload, dict):
            raise TrendyolApiError(f"Trendyol {resource_name} response must be a JSON object")
        return response_payload

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> TrendyolClient:
        return self

    async def __aexit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        await self.close()
