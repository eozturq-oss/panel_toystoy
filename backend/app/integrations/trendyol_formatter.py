from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from ..models import Product
from ..marketplace_preflight import assert_toy_submission_ready


class TrendyolPayloadError(ValueError):
    """Raised when a local product cannot produce a valid Trendyol payload."""


def format_product_payload(
    product: Product,
    *,
    category_mapping: Mapping[str, Any],
    brand_id: int,
    cargo_company_id: int,
) -> dict[str, list[dict[str, Any]]]:
    """Convert a database Product and its variants to Trendyol createProducts JSON."""
    for variant in product.variants:
        assert_toy_submission_ready(
            {
                "barcode": variant.barcode,
                "ce_compliant": product.ce_compliant,
                "age_group": product.age_group,
                "min_age_months": product.min_age_months,
                "gender": product.gender,
                "material": product.material,
                "piece_count": product.piece_count,
            }
        )
    if brand_id <= 0:
        raise TrendyolPayloadError("brand_id must be greater than zero")
    if cargo_company_id <= 0:
        raise TrendyolPayloadError("cargo_company_id must be greater than zero")

    category_id = category_mapping.get("categoryId")
    attributes = category_mapping.get("attributes", [])
    if not isinstance(category_id, int) or category_id <= 0:
        raise TrendyolPayloadError("category_mapping must contain a valid categoryId")
    if not isinstance(attributes, list):
        raise TrendyolPayloadError("category_mapping attributes must be a list")

    variants = [variant for variant in product.variants if variant.active is not False]
    if not variants:
        raise TrendyolPayloadError(f"Product '{product.product_code}' has no active variants")
    if not product.images:
        raise TrendyolPayloadError(f"Product '{product.product_code}' has no images")

    images = [{"url": image.url} for image in product.images]
    items: list[dict[str, Any]] = []
    for variant in variants:
        items.append(
            {
                "barcode": variant.barcode,
                "title": product.title,
                "productMainId": product.product_code,
                "brandId": brand_id,
                "categoryId": category_id,
                "quantity": variant.stock_quantity,
                "stockCode": variant.sku,
                "dimensionalWeight": _json_number(variant.desi),
                "description": product.description or product.title,
                "currencyType": "TRY",
                "listPrice": _json_number(variant.list_price or variant.sale_price),
                "salePrice": _json_number(variant.sale_price),
                "vatRate": _json_number(product.vat_rate),
                "cargoCompanyId": cargo_company_id,
                "images": images,
                "attributes": attributes,
            }
        )

    return {"items": items}


def _json_number(value: Decimal | int | float) -> int | float:
    number = float(value)
    return int(number) if number.is_integer() else number
