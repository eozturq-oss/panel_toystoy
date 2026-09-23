from __future__ import annotations

import asyncio
from decimal import Decimal
import uuid

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db import Base
from app.models import MarketplaceOperationLog, Notification, ProductVariant
from app.services.marketplace_logger import MarketplaceLogger, redact_payload
from app.services.notification_service import NotificationService


def test_logger_redacts_credentials_and_records_success() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    tenant_id = uuid.uuid4()
    with Session(engine) as db:
        logger = MarketplaceLogger(db)
        record = logger.start(
            tenant_id=tenant_id,
            marketplace_code="trendyol",
            operation="CREATE_PRODUCTS",
            request_payload={"api_key": "secret", "items": [{"barcode": "8690000000001"}]},
        )
        logger.succeed(record, batch_request_id="batch-1", http_status=200)
        stored = db.scalar(select(MarketplaceOperationLog).where(MarketplaceOperationLog.id == record.id))
        assert stored is not None
        assert stored.status == "SUCCESS"
        assert stored.batch_request_id == "batch-1"
        assert stored.request_payload["api_key"] == "[REDACTED]"


def test_notifications_support_stock_depleted_and_read_state() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    tenant_id = uuid.uuid4()
    with Session(engine) as db:
        variant = ProductVariant(
            id=uuid.uuid4(), product_id=uuid.uuid4(), sku="SKU-1",
            barcode="8690000000001", desi=1, stock_quantity=0,
            sale_price=Decimal("99.90"),
        )
        notification = NotificationService(db).notify_stock_depleted(
            tenant_id=tenant_id, variant=variant, marketplace_code="TRENDYOL"
        )
        assert notification.notification_type == "STOCK_DEPLETED"
        assert len(NotificationService(db).unread(tenant_id)) == 1
        NotificationService(db).mark_read(tenant_id, notification.id)
        assert NotificationService(db).unread(tenant_id) == []


def test_redact_payload_is_recursive() -> None:
    assert redact_payload({"nested": {"token": "hidden"}}) == {
        "nested": {"token": "[REDACTED]"}
    }
