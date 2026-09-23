from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class MarketplacePreflightError(ValueError):
    """Raised when a toy product is not ready for marketplace submission."""


def validate_toy_submission(product: Mapping[str, Any]) -> list[str]:
    """Return all blocking toy-category validation errors before an API call."""
    errors: list[str] = []
    barcode = str(product.get("barcode", ""))
    if not barcode.isdigit() or len(barcode) not in {8, 12, 13, 14}:
        errors.append("EAN/UPC barcode must contain 8, 12, 13, or 14 digits")
    if product.get("ce_compliant") is not True:
        errors.append("CE compliance must be true")
    age_group = product.get("age_group")
    if not isinstance(age_group, str) or not age_group.strip():
        errors.append("age_group is required")
    min_age = product.get("min_age_months")
    if not isinstance(min_age, int) or min_age < 0:
        errors.append("min_age_months must be a non-negative integer")
    if not product.get("gender"):
        errors.append("gender is required")
    if not product.get("material"):
        errors.append("material is required")
    if not product.get("piece_count") or int(product["piece_count"]) <= 0:
        errors.append("piece_count must be greater than zero")
    return errors


def assert_toy_submission_ready(product: Mapping[str, Any]) -> None:
    errors = validate_toy_submission(product)
    if errors:
        raise MarketplacePreflightError("; ".join(errors))
