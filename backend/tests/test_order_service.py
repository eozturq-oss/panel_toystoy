from __future__ import annotations

import asyncio
from decimal import Decimal
import uuid

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db import Base
from app.models import CustomerOrder, CustomerOrderItem, ProductVariant
from app.services.order_service import OrderFetcher


def make_fetcher(db: Session, variant: ProductVariant) -> OrderFetcher:
    class FakeClient:
        async def fetch_orders(self, *, since: str | None = None) -> list[dict]:
            return []

    return OrderFetcher(db, {"TRENDYOL": FakeClient()}, tenant_id=uuid.uuid4())


def test_order_is_saved_and_stock_decreases_once() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        variant = ProductVariant(
            product_id=uuid.uuid4(), sku="SKU-1", barcode="8690000000001",
            desi=Decimal("1"), stock_quantity=10, sale_price=Decimal("99.90"),
        )
        db.add(variant)
        db.commit()
        fetcher = make_fetcher(db, variant)
        payload = {
            "orderNumber": "TY-100",
            "totalPrice": 199.80,
            "lines": [{"barcode": "8690000000001", "quantity": 2, "price": 99.90}],
        }

        first = fetcher.process_order("Trendyol", payload)
        second = fetcher.process_order("Trendyol", payload)
        db.refresh(variant)

        assert first.status == "PROCESSED"
        assert second.id == first.id
        assert variant.stock_quantity == 8
        assert db.scalar(select(CustomerOrderItem).where(CustomerOrderItem.order_id == first.id)) is not None


def test_unknown_barcode_does_not_make_stock_change_and_logs_error() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        fetcher = make_fetcher(db, ProductVariant())
        order = fetcher.process_order(
            "HEPSIBURADA",
            {"id": "HB-200", "items": [{"productBarcode": "8699999999999", "quantity": 1}]},
        )

        assert order.status == "ERROR"
        assert "no local variant" in (order.error_message or "")
        assert order.marketplace_code == "HEPSIBURADA"


def test_fetcher_polls_all_marketplaces() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    calls: list[str] = []

    class FakeClient:
        def __init__(self, marketplace: str) -> None:
            self.marketplace = marketplace

        async def fetch_orders(self, *, since: str | None = None) -> list[dict]:
            calls.append(self.marketplace)
            return []

    with Session(engine) as db:
        from app.services.order_service import run_order_fetcher

        fetcher = OrderFetcher(
            db,
            {"TRENDYOL": FakeClient("trendyol"), "HEPSIBURADA": FakeClient("hepsiburada")},
            tenant_id=uuid.uuid4(),
        )
        assert asyncio.run(run_order_fetcher(fetcher)) == 0
        assert calls == ["trendyol", "hepsiburada"]
