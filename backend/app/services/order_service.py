from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal
from typing import Any
import asyncio
import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..integrations.base import MarketplaceClient
from ..models import CustomerOrder, CustomerOrderItem, ProductVariant
from .notification_service import NotificationService


class OrderProcessingError(RuntimeError):
    pass


class OrderFetcher:
    """Poll marketplace adapters and persist new orders with stock reservation."""

    def __init__(
        self,
        db: Session,
        clients: Mapping[str, MarketplaceClient],
        *,
        tenant_id: uuid.UUID,
    ) -> None:
        self.db = db
        self.clients = {code.upper(): client for code, client in clients.items()}
        self.tenant_id = tenant_id

    async def fetch_and_process(self, *, since: str | None = None) -> list[CustomerOrder]:
        processed: list[CustomerOrder] = []
        for marketplace, client in self.clients.items():
            orders = await client.fetch_orders(since=since)
            for payload in orders:
                order = self.process_order(marketplace, payload)
                processed.append(order)
        return processed

    def process_order(self, marketplace: str, payload: Mapping[str, Any]) -> CustomerOrder:
        marketplace = marketplace.upper()
        external_id = _first_value(payload, "id", "orderId", "orderNumber")
        if not external_id:
            raise OrderProcessingError("marketplace order has no external order ID")

        existing = self.db.scalar(
            select(CustomerOrder).where(
                CustomerOrder.marketplace_code == marketplace,
                CustomerOrder.external_order_id == str(external_id),
            )
        )
        if existing is not None:
            return existing

        order = CustomerOrder(
            tenant_id=self.tenant_id,
            marketplace_code=marketplace,
            external_order_id=str(external_id),
            status="RECEIVED",
            total_amount=_decimal_or_none(_first_value(payload, "totalPrice", "totalAmount")),
            ordered_at=_datetime_or_none(_first_value(payload, "orderDate", "createdAt")),
            raw_payload=dict(payload),
        )
        self.db.add(order)
        self.db.flush()

        try:
            depleted_variants: list[ProductVariant] = []
            for item_payload in _order_items(payload):
                barcode = str(_first_value(item_payload, "barcode", "productBarcode", "sku") or "")
                quantity = int(_first_value(item_payload, "quantity", "amount") or 0)
                if not barcode or quantity <= 0:
                    raise OrderProcessingError("order item requires barcode and positive quantity")
                variant = self.db.scalar(
                    select(ProductVariant)
                    .where(ProductVariant.barcode == barcode)
                    .with_for_update()
                )
                if variant is None:
                    raise OrderProcessingError(f"no local variant found for barcode {barcode}")
                if variant.stock_quantity < quantity:
                    raise OrderProcessingError(
                        f"insufficient stock for barcode {barcode}: "
                        f"requested {quantity}, available {variant.stock_quantity}"
                    )
                variant.stock_quantity -= quantity
                if variant.stock_quantity == 0:
                    depleted_variants.append(variant)
                order.items.append(
                    CustomerOrderItem(
                        barcode=barcode,
                        quantity=quantity,
                        unit_price=_decimal_or_none(
                            _first_value(item_payload, "price", "unitPrice", "salePrice")
                        ),
                        variant_id=variant.id,
                        raw_payload=dict(item_payload),
                    )
                )
            order.status = "PROCESSED"
            self.db.commit()
            self.db.refresh(order)
            notifications = NotificationService(self.db)
            for depleted_variant in depleted_variants:
                notifications.notify_stock_depleted(
                    tenant_id=self.tenant_id,
                    variant=depleted_variant,
                    marketplace_code=marketplace,
                )
            return order
        except Exception as exc:
            self.db.rollback()
            error_order = self.db.scalar(
                select(CustomerOrder).where(
                    CustomerOrder.marketplace_code == marketplace,
                    CustomerOrder.external_order_id == str(external_id),
                )
            )
            if error_order is None:
                error_order = CustomerOrder(
                    tenant_id=self.tenant_id,
                    marketplace_code=marketplace,
                    external_order_id=str(external_id),
                    status="ERROR",
                    raw_payload=dict(payload),
                    error_message=str(exc),
                )
                self.db.add(error_order)
            else:
                error_order.status = "ERROR"
                error_order.error_message = str(exc)
            self.db.commit()
            self.db.refresh(error_order)
            return error_order


async def run_order_fetcher(fetcher: OrderFetcher, *, since: str | None = None) -> int:
    """Cron-friendly entry point for one polling cycle."""
    return len(await fetcher.fetch_and_process(since=since))


class PeriodicOrderFetcher:
    """Poll all configured marketplaces periodically, defaulting to 15 minutes."""

    def __init__(self, fetcher: OrderFetcher, interval_seconds: int = 900) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be greater than zero")
        self.fetcher = fetcher
        self.interval_seconds = interval_seconds

    async def run_once(self, *, since: str | None = None) -> int:
        return await run_order_fetcher(self.fetcher, since=since)

    async def run_forever(self, *, since: str | None = None) -> None:
        while True:
            await self.run_once(since=since)
            await asyncio.sleep(self.interval_seconds)


def _order_items(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    items = payload.get("lines") or payload.get("items") or payload.get("orderLines") or []
    return [item for item in items if isinstance(item, Mapping)]


def _first_value(payload: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if payload.get(key) is not None:
            return payload[key]
    return None


def _decimal_or_none(value: Any) -> Decimal | None:
    return Decimal(str(value)) if value is not None else None


def _datetime_or_none(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None
