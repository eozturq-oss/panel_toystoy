from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Notification, ProductVariant


class NotificationService:
    """Creates and reads persistent UI notifications for operational events."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def notify_marketplace_failure(
        self,
        *,
        tenant_id: uuid.UUID,
        marketplace_code: str,
        message: str,
        product_id: uuid.UUID | None = None,
        variant_id: uuid.UUID | None = None,
        details: Mapping[str, Any] | None = None,
    ) -> Notification:
        return self._create(
            tenant_id=tenant_id,
            notification_type="MARKETPLACE_FAILURE",
            severity="ERROR",
            title=f"{marketplace_code.title()} gönderimi başarısız",
            message=message,
            marketplace_code=marketplace_code,
            product_id=product_id,
            variant_id=variant_id,
            details=details,
        )

    def notify_stock_depleted(
        self,
        *,
        tenant_id: uuid.UUID,
        variant: ProductVariant,
        marketplace_code: str | None = None,
    ) -> Notification:
        return self._create(
            tenant_id=tenant_id,
            notification_type="STOCK_DEPLETED",
            severity="WARNING",
            title="Stok tükendi",
            message=f"{variant.barcode} barkodlu ürünün stoğu tükendi.",
            marketplace_code=marketplace_code,
            product_id=variant.product_id,
            variant_id=variant.id,
            details={"barcode": variant.barcode, "sku": variant.sku},
        )

    def unread(self, tenant_id: uuid.UUID, *, limit: int = 50) -> list[Notification]:
        return list(
            self.db.scalars(
                select(Notification)
                .where(Notification.tenant_id == tenant_id, Notification.is_read.is_(False))
                .order_by(Notification.created_at.desc())
                .limit(limit)
            ).all()
        )

    def mark_read(self, tenant_id: uuid.UUID, notification_id: uuid.UUID) -> Notification | None:
        notification = self.db.scalar(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.tenant_id == tenant_id,
            )
        )
        if notification is None:
            return None
        notification.is_read = True
        notification.read_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(notification)
        return notification

    def _create(self, **values: Any) -> Notification:
        notification = Notification(**values)
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        return notification
