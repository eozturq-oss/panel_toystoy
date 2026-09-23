"""Build marketplace payloads without making any network/API call.

Run from the repository root:
    python scripts/dry_run_marketplace.py --marketplace all
"""
from __future__ import annotations

import argparse
from decimal import Decimal
import json
import sys
from pathlib import Path

runtime_root = Path(__file__).resolve().parents[1]
backend_root = runtime_root / "backend"
sys.path.insert(0, str(backend_root if (backend_root / "app").exists() else runtime_root))

from app.integrations.hepsiburada_mapper import HepsiburadaToyMapper
from app.integrations.trendyol_formatter import format_product_payload
from app.marketplace_preflight import validate_toy_submission
from app.models import Product, ProductImage, ProductVariant


def build_sample_product() -> Product:
    product = Product(
        product_code="DRY-RUN-TOY-001",
        title="Renkli Yapı Blokları",
        description="Dry-run oyuncak ürünü",
        brand="ToyStore",
        material="ABS Plastik",
        age_group="3-6 Yaş",
        min_age_months=36,
        gender="Unisex",
        piece_count=60,
        ce_compliant=True,
        vat_rate=Decimal("20"),
    )
    product.images.append(ProductImage(url="https://cdn.example.test/dry-run/main.jpg"))
    product.variants.append(
        ProductVariant(
            sku="DRY-RUN-TOY-001",
            barcode="8690000000001",
            desi=Decimal("2.5"),
            stock_quantity=10,
            sale_price=Decimal("349.90"),
            list_price=Decimal("399.90"),
        )
    )
    return product


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate payloads without marketplace calls")
    parser.add_argument("--marketplace", choices=("trendyol", "hepsiburada", "all"), default="all")
    args = parser.parse_args()
    product = build_sample_product()
    errors = validate_toy_submission(
        {
            "barcode": product.variants[0].barcode,
            "ce_compliant": product.ce_compliant,
            "age_group": product.age_group,
            "min_age_months": product.min_age_months,
            "gender": product.gender,
            "material": product.material,
            "piece_count": product.piece_count,
        }
    )
    if errors:
        print(json.dumps({"dry_run": False, "errors": errors}, ensure_ascii=False, indent=2))
        return 1

    output: dict[str, object] = {"dry_run": True, "api_calls": 0, "preflight": "passed"}
    if args.marketplace in {"trendyol", "all"}:
        output["trendyol"] = format_product_payload(
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
    if args.marketplace in {"hepsiburada", "all"}:
        output["hepsiburada"] = HepsiburadaToyMapper().map_product_attributes(
            category_id="TOY-CONSTRUCTION",
            product={
                "age_group": product.age_group,
                "gender": product.gender,
                "ce_compliant": product.ce_compliant,
                "piece_count": product.piece_count,
                "material": product.material,
            },
        )
    print(json.dumps(output, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
