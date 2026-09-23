from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..integrations.trendyol import TrendyolClient
from ..models import TrendyolBatchError, TrendyolBatchRequest


SUCCESS_STATUSES = {"COMPLETED", "SUCCESS", "SUCCEEDED", "DONE"}
FAILURE_STATUSES = {"FAILED", "FAILURE", "ERROR"}


async def check_and_log_batch_status(
    db: Session,
    client: TrendyolClient,
    *,
    tenant_id: uuid.UUID,
    batch_request_id: str,
) -> TrendyolBatchRequest:
    """Fetch a Trendyol batch, normalize its status, and persist all item errors."""
    response = await client.get_batch_status(batch_request_id)
    status = normalize_batch_status(response)

    batch = db.scalar(
        select(TrendyolBatchRequest).where(
            TrendyolBatchRequest.batch_request_id == batch_request_id
        )
    )
    if batch is None:
        batch = TrendyolBatchRequest(
            tenant_id=tenant_id,
            batch_request_id=batch_request_id,
        )
        db.add(batch)

    batch.status = status
    batch.raw_response = dict(response)
    batch.errors.clear()
    for error in extract_batch_errors(response):
        batch.errors.append(TrendyolBatchError(**error))

    db.commit()
    db.refresh(batch)
    return batch


def normalize_batch_status(response: Mapping[str, Any]) -> str:
    """Return PENDING, SUCCESS, FAILED, or UNKNOWN for UI and reporting."""
    raw_status = str(response.get("status", "")).upper()
    if raw_status in SUCCESS_STATUSES:
        return "SUCCESS"
    if raw_status in FAILURE_STATUSES or extract_batch_errors(response):
        return "FAILED"
    if raw_status in {"IN_PROGRESS", "PROCESSING", "PENDING", "QUEUED"}:
        return "PENDING"
    return "UNKNOWN"


def extract_batch_errors(response: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Convert Trendyol failure arrays into database-ready error records."""
    candidates: Any = response.get("failureReasons")
    if candidates is None:
        candidates = response.get("errors", response.get("failureReason"))
    if isinstance(candidates, Mapping):
        candidates = [candidates]
    if not isinstance(candidates, Sequence) or isinstance(candidates, (str, bytes)):
        return []

    errors: list[dict[str, Any]] = []
    for candidate in candidates:
        if isinstance(candidate, Mapping):
            message = candidate.get("message") or candidate.get("errorMessage") or candidate.get("reason")
            if not message:
                message = str(candidate)
            errors.append(
                {
                    "barcode": _optional_string(candidate.get("barcode")),
                    "stock_code": _optional_string(candidate.get("stockCode") or candidate.get("sku")),
                    "error_code": _optional_string(candidate.get("errorCode") or candidate.get("code")),
                    "error_message": str(message),
                    "raw_error": dict(candidate),
                }
            )
        elif candidate:
            errors.append(
                {
                    "error_message": str(candidate),
                    "raw_error": {"message": str(candidate)},
                }
            )
    return errors


def _optional_string(value: Any) -> str | None:
    return str(value) if value is not None else None
