from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.models import MarketplaceListing, Product, ProductVariant
from app.services.inventory_sync import InventorySyncService, _format_marketplace_payload
from app.services.queue_manager import QueueManager


class FakeClient:
    def __init__(self) -> None:
        self.payloads: list[dict] = []

    async def update_price_and_inventory(self, payload: dict) -> str:
        self.payloads.append(payload)
        return "batch-1"


async def _successful_queue_run() -> list[str]:
    queue = QueueManager(max_retries=0)
    calls: list[str] = []
    await queue.enqueue("TRENDYOL", lambda: _record(calls, "first"), priority=5)
    await queue.enqueue("TRENDYOL", lambda: _record(calls, "second"), priority=1)
    results = await queue.drain()
    assert calls == ["second", "first"]
    return results


async def _record(calls: list[str], value: str) -> str:
    calls.append(value)
    return value


def test_queue_processes_priority_and_retries() -> None:
    assert asyncio.run(_successful_queue_run()) == ["second", "first"]


def test_marketplace_payloads_are_lightweight_and_different() -> None:
    updates = [{"barcode": "8690000000001", "merchantSku": "SKU-1", "quantity": 4, "salePrice": 99.9, "listPrice": 120.0}]
    assert _format_marketplace_payload("TRENDYOL", updates) == {
        "items": [{"barcode": "8690000000001", "quantity": 4, "salePrice": 99.9, "listPrice": 120.0}]
    }
    assert _format_marketplace_payload("HEPSIBURADA", updates) == {
        "items": [{"merchantSku": "SKU-1", "quantity": 4, "price": 99.9}]
    }


def test_scheduler_queues_only_unsynced_variants() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    marketplace_id = uuid.uuid4()
    product_id = uuid.uuid4()
    variant_id = uuid.uuid4()
    with Session(engine) as db:
        product = Product(
            id=product_id, tenant_id=uuid.uuid4(), product_code="TOY-1", title="Toy",
            brand="Brand", material="Plastic", age_group="3+", min_age_months=36,
            gender="Unisex", piece_count=1, ce_compliant=True,
        )
        variant = ProductVariant(
            id=variant_id, product=product, sku="SKU-1", barcode="8690000000001",
            desi=1, stock_quantity=4, sale_price=99,
        )
        listing = MarketplaceListing(variant=variant, marketplace_id=marketplace_id)
        db.add_all([product, variant, listing])
        db.commit()
        client = FakeClient()
        service = InventorySyncService(
            db, {str(marketplace_id): client}, QueueManager(max_retries=0)
        )
        queued = asyncio.run(service.enqueue_changed_inventory())
        assert queued == 1
        asyncio.run(service.queue.drain())
        assert client.payloads == [{"items": [{"barcode": "8690000000001", "quantity": 4, "salePrice": 99.0, "listPrice": 99.0}]}]
        assert listing.inventory_synced_at is not None
