from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db import Base
from app.models import TrendyolBatchError, TrendyolBatchRequest
from app.services.trendyol_batch_service import (
    check_and_log_batch_status,
    normalize_batch_status,
)


class FakeTrendyolClient:
    async def get_batch_status(self, batch_request_id: str) -> dict[str, object]:
        assert batch_request_id == "batch-123"
        return {
            "status": "FAILED",
            "failureReasons": [
                {
                    "barcode": "8690000000001",
                    "stockCode": "TOY-BLOCK-001-STD",
                    "errorCode": "DUPLICATE_BARCODE",
                    "message": "Barkod zaten var",
                },
                {"message": "Yaş grubu alanı zorunludur"},
            ],
        }


def test_batch_errors_are_normalized_and_persisted() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    tenant_id = uuid.uuid4()

    with Session(engine) as db:
        batch = asyncio.run(
            check_and_log_batch_status(
                db,
                FakeTrendyolClient(),
                tenant_id=tenant_id,
                batch_request_id="batch-123",
            )
        )

        assert batch.status == "FAILED"
        errors = db.scalars(
            select(TrendyolBatchError).where(TrendyolBatchError.batch_id == batch.id)
        ).all()
        assert [error.error_message for error in errors] == [
            "Barkod zaten var",
            "Yaş grubu alanı zorunludur",
        ]
        assert errors[0].barcode == "8690000000001"
        assert errors[0].error_code == "DUPLICATE_BARCODE"


def test_normalize_batch_status() -> None:
    assert normalize_batch_status({"status": "COMPLETED"}) == "SUCCESS"
    assert normalize_batch_status({"status": "PROCESSING"}) == "PENDING"
    assert normalize_batch_status({"status": "FAILED"}) == "FAILED"
