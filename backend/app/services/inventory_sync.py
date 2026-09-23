from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any
import asyncio
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..integrations.base import MarketplaceClient
from ..models import Marketplace, MarketplaceListing, ProductVariant
from .queue_manager import QueueManager
from .marketplace_logger import MarketplaceLogger
from .notification_service import NotificationService


class InventorySyncService:
    def __init__(
        self,
        db: Session,
        clients: Mapping[str, MarketplaceClient],
        queue: QueueManager,
        *,
        tenant_id=None,
        logger: MarketplaceLogger | None = None,
        notifications: NotificationService | None = None,
    ) -> None:
        self.db = db
        self.clients = {name.upper(): client for name, client in clients.items()}
        self.queue = queue
        self.tenant_id = tenant_id
        self.logger = logger
        self.notifications = notifications

    async def enqueue_changed_inventory(self) -> int:
        """Queue one bulk update per marketplace for variants changed since last sync."""
        jobs = 0
        for marketplace, client in self.clients.items():
            updates, listings = self._changed_updates(marketplace)
            if not updates:
                continue
            payload = _format_marketplace_payload(marketplace, updates)

            async def send(
                client: MarketplaceClient = client,
                marketplace: str = marketplace,
                payload: dict[str, Any] = payload,
                listings: list[MarketplaceListing] = listings,
            ) -> str:
                log_record = None
                if self.logger is not None and self.tenant_id is not None:
                    log_record = self.logger.start(
                        tenant_id=self.tenant_id,
                        marketplace_code=marketplace,
                        operation="UPDATE_PRICE_AND_INVENTORY",
                        request_payload=payload,
                    )
                try:
                    batch_id = await client.update_price_and_inventory(payload)
                except Exception as exc:
                    if log_record is not None:
                        self.logger.fail(log_record, exc)
                    if self.notifications is not None and self.tenant_id is not None:
                        self.notifications.notify_marketplace_failure(
                            tenant_id=self.tenant_id,
                            marketplace_code=marketplace,
                            message=str(exc),
                            details={"operation": "UPDATE_PRICE_AND_INVENTORY"},
                        )
                    raise
                if log_record is not None:
                    self.logger.succeed(log_record, batch_request_id=batch_id)
                synced_at = datetime.now(timezone.utc)
                for listing in listings:
                    listing.inventory_synced_at = synced_at
                self.db.commit()
                return batch_id

            await self.queue.enqueue(marketplace, send)
            jobs += 1
        return jobs

    def _changed_updates(
        self, marketplace: str
    ) -> tuple[list[dict[str, Any]], list[MarketplaceListing]]:
        rows = self.db.execute(
            select(ProductVariant, MarketplaceListing)
            .join(MarketplaceListing, MarketplaceListing.variant_id == ProductVariant.id)
            .join(Marketplace, Marketplace.id == MarketplaceListing.marketplace_id, isouter=True)
            .where(
                _marketplace_filter(marketplace),
                ProductVariant.active.is_(True),
                (
                    MarketplaceListing.inventory_synced_at.is_(None)
                    | (ProductVariant.inventory_updated_at > MarketplaceListing.inventory_synced_at)
                ),
            )
        ).all()
        updates = [
            {
                "barcode": variant.barcode,
                "merchantSku": variant.sku,
                "quantity": variant.stock_quantity,
                "salePrice": float(variant.sale_price),
                "listPrice": float(variant.list_price or variant.sale_price),
            }
            for variant, _listing in rows
        ]
        return updates, [listing for _variant, listing in rows]


class PeriodicInventoryScheduler:
    """Runs inventory synchronization on a fixed interval, e.g. every 900 seconds."""

    def __init__(self, sync_service: InventorySyncService, interval_seconds: int = 900) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be greater than zero")
        self.sync_service = sync_service
        self.interval_seconds = interval_seconds

    async def run_once(self) -> int:
        queued = await self.sync_service.enqueue_changed_inventory()
        await self.sync_service.queue.drain()
        return queued

    async def run_forever(self) -> None:
        while True:
            await self.run_once()
            await asyncio.sleep(self.interval_seconds)


async def run_inventory_cron(sync_service: InventorySyncService) -> int:
    """Cron-friendly entry point: execute one sync cycle and exit."""
    scheduler = PeriodicInventoryScheduler(sync_service)
    return await scheduler.run_once()


def _format_marketplace_payload(
    marketplace: str, updates: list[dict[str, Any]]
) -> dict[str, list[dict[str, Any]]]:
    if marketplace == "HEPSIBURADA":
        return {
            "items": [
                {
                    "merchantSku": update["merchantSku"],
                    "quantity": update["quantity"],
                    "price": update["salePrice"],
                }
                for update in updates
            ]
        }
    return {
        "items": [
            {
                "barcode": update["barcode"],
                "quantity": update["quantity"],
                "salePrice": update["salePrice"],
                "listPrice": update["listPrice"],
            }
            for update in updates
        ]
    }


def _marketplace_filter(value: str):
    try:
        return MarketplaceListing.marketplace_id == uuid.UUID(value)
    except (ValueError, AttributeError):
        return Marketplace.code == value


