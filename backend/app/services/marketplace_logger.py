from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from datetime import datetime, timezone
from typing import Any, TypeVar
import uuid

from sqlalchemy.orm import Session

from ..models import MarketplaceOperationLog

T = TypeVar("T")
SENSITIVE_KEYS = {"password", "secret", "api_key", "apikey", "authorization", "token"}


class MarketplaceLogger:
    """Persists marketplace operation audit records without leaking credentials."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def start(
        self,
        *,
        tenant_id: uuid.UUID,
        marketplace_code: str,
        operation: str,
        request_payload: Mapping[str, Any] | None = None,
        product_id: uuid.UUID | None = None,
        variant_id: uuid.UUID | None = None,
        barcode: str | None = None,
    ) -> MarketplaceOperationLog:
        record = MarketplaceOperationLog(
            tenant_id=tenant_id,
            marketplace_code=marketplace_code.upper(),
            operation=operation,
            status="STARTED",
            product_id=product_id,
            variant_id=variant_id,
            barcode=barcode,
            request_payload=redact_payload(request_payload or {}),
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def succeed(
        self,
        record: MarketplaceOperationLog,
        *,
        response_payload: Mapping[str, Any] | None = None,
        batch_request_id: str | None = None,
        http_status: int | None = None,
    ) -> MarketplaceOperationLog:
        record.status = "SUCCESS"
        record.response_payload = redact_payload(response_payload or {})
        record.batch_request_id = batch_request_id
        record.http_status = http_status
        record.completed_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(record)
        return record

    def fail(
        self,
        record: MarketplaceOperationLog,
        error: Exception | str,
        *,
        response_payload: Mapping[str, Any] | None = None,
        http_status: int | None = None,
    ) -> MarketplaceOperationLog:
        record.status = "FAILED"
        record.error_message = str(error)
        record.response_payload = redact_payload(response_payload or {})
        record.http_status = http_status
        record.completed_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(record)
        return record

    async def execute(
        self,
        *,
        tenant_id: uuid.UUID,
        marketplace_code: str,
        operation: str,
        action: Callable[[], Awaitable[T]],
        request_payload: Mapping[str, Any] | None = None,
        product_id: uuid.UUID | None = None,
        variant_id: uuid.UUID | None = None,
        barcode: str | None = None,
    ) -> T:
        record = self.start(
            tenant_id=tenant_id,
            marketplace_code=marketplace_code,
            operation=operation,
            request_payload=request_payload,
            product_id=product_id,
            variant_id=variant_id,
            barcode=barcode,
        )
        try:
            result = await action()
            batch_id = result if isinstance(result, str) else None
            self.succeed(record, batch_request_id=batch_id)
            return result
        except Exception as exc:
            self.fail(record, exc)
            raise


def redact_payload(value: Any, *, key: str | None = None) -> Any:
    """Recursively remove credentials from audit payloads."""
    if key and key.casefold() in SENSITIVE_KEYS:
        return "[REDACTED]"
    if isinstance(value, Mapping):
        return {str(item_key): redact_payload(item_value, key=str(item_key)) for item_key, item_value in value.items()}
    if isinstance(value, list):
        return [redact_payload(item) for item in value]
    return value
