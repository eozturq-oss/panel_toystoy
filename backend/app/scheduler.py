from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
import os
import uuid

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .config import get_settings
from .db import SessionLocal
from .integrations.hepsiburada import HepsiburadaClient
from .integrations.trendyol import TrendyolClient
from .services.inventory_sync import InventorySyncService, PeriodicInventoryScheduler
from .services.order_service import OrderFetcher
from .services.queue_manager import QueueManager

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


async def run_automation_cycle(
    orders: OrderFetcher,
    inventory: InventorySyncService,
) -> tuple[int, int]:
    """Process new orders first, then broadcast every changed stock quantity."""
    processed_orders = await orders.fetch_and_process()
    queued_updates = await PeriodicInventoryScheduler(inventory).run_once()
    return len(processed_orders), queued_updates


async def run() -> None:
    settings = get_settings()
    tenant_id = uuid.UUID(os.environ["DEFAULT_TENANT_ID"])
    trendyol = TrendyolClient(settings)
    hepsiburada = HepsiburadaClient(settings)
    clients = {"TRENDYOL": trendyol, "HEPSIBURADA": hepsiburada}
    queue = QueueManager(requests_per_minute={"TRENDYOL": 30, "HEPSIBURADA": 30})
    interval_seconds = int(os.getenv("MARKETPLACE_POLL_INTERVAL_SECONDS", "900"))
    if interval_seconds <= 0:
        raise ValueError("MARKETPLACE_POLL_INTERVAL_SECONDS must be greater than zero")

    async def run_cycle() -> None:
        try:
            with SessionLocal() as db:
                inventory = InventorySyncService(db, clients, queue, tenant_id=tenant_id)
                orders = OrderFetcher(db, clients, tenant_id=tenant_id)
                processed, queued = await run_automation_cycle(orders, inventory)
                logger.info(
                    "Marketplace automation cycle complete: orders=%s, inventory_jobs=%s",
                    processed,
                    queued,
                )
        except Exception:
            logger.exception("Marketplace automation cycle failed")

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_cycle,
        "interval",
        seconds=interval_seconds,
        id="marketplace-order-inventory-sync",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=60,
        next_run_time=datetime.now(timezone.utc),
    )
    scheduler.start()
    try:
        await asyncio.Event().wait()
    finally:
        scheduler.shutdown(wait=True)
        await trendyol.close()
        await hepsiburada.close()


if __name__ == "__main__":
    asyncio.run(run())
