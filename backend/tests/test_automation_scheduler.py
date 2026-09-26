from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.models import Marketplace, MarketplaceListing, Product, ProductVariant
from app.scheduler import run_automation_cycle
from app.services.inventory_sync import InventorySyncService
from app.services.order_service import OrderFetcher
from app.services.queue_manager import QueueManager


class FakeMarketplaceClient:
    def __init__(self, orders: list[dict]) -> None:
        self.orders = orders
        self.inventory_payloads: list[dict] = []

    async def fetch_orders(self, *, since: str | None = None) -> list[dict]:
        assert since is None
        return self.orders

    async def update_price_and_inventory(self, payload: dict) -> str:
        self.inventory_payloads.append(payload)
        return "batch-1"


def test_automation_cycle_decrements_then_syncs_all_marketplaces() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    tenant_id = uuid.uuid4()
    synced_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
    clients = {
        "TRENDYOL": FakeMarketplaceClient(
            [{"orderNumber": "TY-300", "lines": [{"barcode": "8690000000001", "quantity": 2}]}]
        ),
        "HEPSIBURADA": FakeMarketplaceClient([]),
    }

    with Session(engine) as db:
        product = Product(
            tenant_id=tenant_id,
            product_code="TOY-1",
            title="Toy",
            brand="Brand",
            material="Plastic",
            age_group="3+",
            min_age_months=36,
            gender="Unisex",
            piece_count=1,
            ce_compliant=True,
        )
        variant = ProductVariant(
            product=product,
            sku="SKU-1",
            barcode="8690000000001",
            desi=Decimal("1"),
            stock_quantity=5,
            sale_price=Decimal("99.90"),
            inventory_updated_at=synced_at,
        )
        trendyol = Marketplace(code="TRENDYOL", name="Trendyol")
        hepsiburada = Marketplace(code="HEPSIBURADA", name="Hepsiburada")
        db.add_all([product, variant, trendyol, hepsiburada])
        db.flush()
        db.add_all(
            [
                MarketplaceListing(
                    variant=variant, marketplace_id=trendyol.id, inventory_synced_at=synced_at
                ),
                MarketplaceListing(
                    variant=variant, marketplace_id=hepsiburada.id, inventory_synced_at=synced_at
                ),
            ]
        )
        db.commit()

        orders = OrderFetcher(db, clients, tenant_id=tenant_id)
        inventory = InventorySyncService(
            db,
            clients,
            QueueManager(max_retries=0),
            tenant_id=tenant_id,
        )
        processed, queued = asyncio.run(run_automation_cycle(orders, inventory))

        db.refresh(variant)
        assert processed == 1
        assert queued == 2
        assert variant.stock_quantity == 3
        assert clients["TRENDYOL"].inventory_payloads[0]["items"][0]["quantity"] == 3
        assert clients["HEPSIBURADA"].inventory_payloads[0]["items"][0]["quantity"] == 3