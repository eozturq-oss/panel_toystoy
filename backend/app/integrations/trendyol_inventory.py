from __future__ import annotations

from collections.abc import Iterable, Mapping
from decimal import Decimal
from typing import Any

from ..models import ProductVariant


class TrendyolInventoryPayloadError(ValueError):
    """Raised when stock or price data is invalid for Trendyol."""


def format_inventory_update(
    *,
    barcode: str,
    quantity: int,
    sale_price: Decimal | int | float,
    list_price: Decimal | int | float | None = None,
) -> dict[str, Any]:
    """Create one lightweight Trendyol stock/price update item."""
    return _format_item(
        barcode=barcode,
        quantity=quantity,
        sale_price=sale_price,
        list_price=list_price,
    )


def format_bulk_inventory_update(
    updates: Iterable[Mapping[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Create a Trendyol price-and-inventory payload for multiple products."""
    items = [
        _format_item(
            barcode=str(update.get("barcode", "")),
            quantity=update.get("quantity"),
            sale_price=update.get("salePrice", update.get("sale_price")),
            list_price=update.get("listPrice", update.get("list_price")),
        )
        for update in updates
    ]
    if not items:
        raise TrendyolInventoryPayloadError("at least one inventory update is required")
    return {"items": items}


def format_variant_inventory_update(variant: ProductVariant) -> dict[str, Any]:
    """Convert one persisted product variant into a lightweight update item."""
    return format_inventory_update(
        barcode=variant.barcode,
        quantity=variant.stock_quantity,
        sale_price=variant.sale_price,
        list_price=variant.list_price,
    )


def format_variant_bulk_inventory_update(
    variants: Iterable[ProductVariant],
) -> dict[str, list[dict[str, Any]]]:
    """Convert persisted variants into one bulk update payload."""
    return format_bulk_inventory_update(
        format_variant_inventory_update(variant) for variant in variants
    )


def _format_item(
    *,
    barcode: str,
    quantity: Any,
    sale_price: Any,
    list_price: Any,
) -> dict[str, Any]:
    if not barcode or not barcode.isdigit():
        raise TrendyolInventoryPayloadError("barcode must contain only digits")
    if quantity is None or isinstance(quantity, bool) or int(quantity) < 0:
        raise TrendyolInventoryPayloadError("quantity must be a non-negative integer")
    if sale_price is None or Decimal(str(sale_price)) <= 0:
        raise TrendyolInventoryPayloadError("sale_price must be greater than zero")
    if list_price is not None and Decimal(str(list_price)) <= 0:
        raise TrendyolInventoryPayloadError("list_price must be greater than zero")

    item: dict[str, Any] = {
        "barcode": barcode,
        "quantity": int(quantity),
        "salePrice": _json_number(sale_price),
    }
    if list_price is not None:
        item["listPrice"] = _json_number(list_price)
    return item


def _json_number(value: Decimal | int | float) -> int | float:
    number = float(value)
    return int(number) if number.is_integer() else number
