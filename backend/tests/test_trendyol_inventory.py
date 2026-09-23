from __future__ import annotations

from decimal import Decimal
import uuid

import pytest

from app.integrations.trendyol_inventory import (
    TrendyolInventoryPayloadError,
    format_bulk_inventory_update,
    format_inventory_update,
)
from app.models import ProductVariant


def test_formats_single_lightweight_inventory_update() -> None:
    payload = format_inventory_update(
        barcode="8690000000001",
        quantity=18,
        sale_price=Decimal("349.90"),
        list_price=Decimal("399.90"),
    )

    assert payload == {
        "barcode": "8690000000001",
        "quantity": 18,
        "salePrice": 349.9,
        "listPrice": 399.9,
    }


def test_formats_bulk_inventory_update_without_product_fields() -> None:
    payload = format_bulk_inventory_update(
        [
            {"barcode": "8690000000001", "quantity": 18, "sale_price": Decimal("349.90")},
            {"barcode": "8690000000002", "quantity": 0, "salePrice": 99.90},
        ]
    )

    assert payload == {
        "items": [
            {"barcode": "8690000000001", "quantity": 18, "salePrice": 349.9},
            {"barcode": "8690000000002", "quantity": 0, "salePrice": 99.9},
        ]
    }


def test_formats_bulk_updates_from_variants() -> None:
    variants = [
        ProductVariant(
            product_id=uuid.uuid4(),
            sku="SKU-1",
            barcode="8690000000001",
            desi=Decimal("1.00"),
            stock_quantity=7,
            sale_price=Decimal("120.00"),
        )
    ]
    from app.integrations.trendyol_inventory import format_variant_bulk_inventory_update

    assert format_variant_bulk_inventory_update(variants) == {
        "items": [{"barcode": "8690000000001", "quantity": 7, "salePrice": 120}]
    }


def test_rejects_invalid_inventory_data() -> None:
    with pytest.raises(TrendyolInventoryPayloadError):
        format_inventory_update(
            barcode="not-a-barcode",
            quantity=1,
            sale_price=100,
        )

    with pytest.raises(TrendyolInventoryPayloadError):
        format_bulk_inventory_update([])
