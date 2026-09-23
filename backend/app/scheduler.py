from __future__ import annotations

import asyncio
import logging
import os
import uuid

from .config import get_settings
from .db import SessionLocal
from .integrations.hepsiburada import HepsiburadaClient
from .integrations.trendyol import TrendyolClient
from .services.inventory_sync import InventorySyncService, PeriodicInventoryScheduler
from .services.order_service import OrderFetcher, PeriodicOrderFetcher
from .services.queue_manager import QueueManager

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


async def run() -> None:
    settings = get_settings()
    tenant_id = uuid.UUID(os.environ["DEFAULT_TENANT_ID"])
    trendyol = TrendyolClient(settings)
    hepsiburada = HepsiburadaClient(settings)
    clients = {"TRENDYOL": trendyol, "HEPSIBURADA": hepsiburada}
    queue = QueueManager(requests_per_minute={"TRENDYOL": 30, "HEPSIBURADA": 30})

    try:
        while True:
            with SessionLocal() as db:
                inventory = InventorySyncService(db, clients, queue, tenant_id=tenant_id)
                orders = OrderFetcher(db, clients, tenant_id=tenant_id)
                await PeriodicInventoryScheduler(inventory, interval_seconds=900).run_once()
                await PeriodicOrderFetcher(orders, interval_seconds=900).run_once()
            await asyncio.sleep(900)
    finally:
        await trendyol.close()
        await hepsiburada.close()


if __name__ == "__main__":
    asyncio.run(run())
