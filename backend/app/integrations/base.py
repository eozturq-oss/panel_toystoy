from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any


class MarketplaceClient(ABC):
    """Common contract implemented by marketplace adapters."""

    @abstractmethod
    async def create_products(self, payload: Mapping[str, Any]) -> str:
        """Submit products and return the marketplace batch identifier."""
        raise NotImplementedError

    @abstractmethod
    async def update_price_and_inventory(self, payload: Mapping[str, Any]) -> str:
        """Submit stock and price updates and return the batch identifier."""
        raise NotImplementedError

    @abstractmethod
    async def get_categories(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def get_category_attributes(self, category_id: int) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def fetch_orders(self, *, since: str | None = None) -> list[dict[str, Any]]:
        """Fetch normalized or raw new orders from the marketplace."""
        raise NotImplementedError

    @abstractmethod
    async def close(self) -> None:
        raise NotImplementedError

    async def __aenter__(self) -> MarketplaceClient:
        return self

    async def __aexit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        await self.close()
