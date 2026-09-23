from __future__ import annotations

from decimal import Decimal
import uuid

from app.integrations.trendyol_formatter import format_product_payload
from app.models import Product, ProductImage, ProductVariant


def test_formats_toy_product_for_create_products() -> None:
    product = Product(
        tenant_id=uuid.uuid4(),
        product_code="TOY-BLOCK-001",
        title="Renkli Yapı Blokları",
        description="60 parçalı yapı seti",
        brand="ToyStore",
        material="ABS Plastik",
        age_group="3-6 Yaş",
        min_age_months=36,
        gender="Unisex",
        piece_count=60,
        ce_compliant=True,
        vat_rate=Decimal("20.00"),
        images=[ProductImage(url="https://cdn.example.test/toy-main.jpg", is_main=True)],
        variants=[
            ProductVariant(
                sku="TOY-BLOCK-001-STD",
                barcode="8690000000001",
                desi=Decimal("2.50"),
                stock_quantity=25,
                sale_price=Decimal("349.90"),
                list_price=Decimal("399.90"),
            )
        ],
    )

    payload = format_product_payload(
        product,
        category_mapping={
            "categoryId": 245,
            "attributes": [
                {"attributeId": 10, "attributeValueId": 101},
                {"attributeId": 11, "attributeValueId": 202},
            ],
        },
        brand_id=77,
        cargo_company_id=9,
    )

    item = payload["items"][0]
    assert item["barcode"] == "8690000000001"
    assert item["quantity"] == 25
    assert item["dimensionalWeight"] == 2.5
    assert item["salePrice"] == 349.9
    assert item["images"] == [{"url": "https://cdn.example.test/toy-main.jpg"}]
    assert item["attributes"] == [
        {"attributeId": 10, "attributeValueId": 101},
        {"attributeId": 11, "attributeValueId": 202},
    ]
