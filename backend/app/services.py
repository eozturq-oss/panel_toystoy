from __future__ import annotations

from decimal import Decimal
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Product, ProductVariant


def create_sample_toy_product(db: Session, tenant_id: uuid.UUID) -> Product:
    """Create and persist a valid sample toy product with one variant."""
    existing_product = db.scalar(
        select(Product).where(
            Product.tenant_id == tenant_id,
            Product.product_code == "TOY-BLOCK-001",
        )
    )
    if existing_product is not None:
        return existing_product

    product = Product(
        tenant_id=tenant_id,
        product_code="TOY-BLOCK-001",
        title="Renkli Yapı Blokları 60 Parça",
        description="Çocukların yaratıcılığını geliştiren renkli yapı blokları.",
        brand="ToyStore",
        material="ABS Plastik",
        age_group="3-6 Yaş",
        min_age_months=36,
        gender="Unisex",
        license_character=None,
        piece_count=60,
        ce_compliant=True,
        safety_warning="3 yaş altı çocuklar için uygun değildir. Küçük parça içerir.",
        attributes={"toy_type": "construction_set", "origin_country": "TR"},
    )
    product.variants.append(
        ProductVariant(
            sku="TOY-BLOCK-001-STD",
            barcode="8690000000001",
            variant_name="Standart Paket",
            desi=Decimal("2.50"),
            stock_quantity=25,
            sale_price=Decimal("349.90"),
            list_price=Decimal("399.90"),
        )
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product
