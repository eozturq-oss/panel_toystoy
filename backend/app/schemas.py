from __future__ import annotations

from decimal import Decimal
from typing import Any
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ToyProductFields(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    brand: str = Field(min_length=1, max_length=200)
    material: str = Field(min_length=1, max_length=200)
    age_group: str = Field(min_length=1, max_length=100)
    min_age_months: int = Field(ge=0)
    gender: str = Field(min_length=1, max_length=50)
    piece_count: int = Field(gt=0)
    ce_compliant: bool
    safety_warning: str = Field(min_length=1)


class ProductUpdate(ToyProductFields):
    barcode: str | None = Field(default=None, min_length=8, max_length=14)
    sale_price: Decimal | None = Field(default=None, gt=0)
    stock_quantity: int | None = Field(default=None, ge=0)

    @field_validator("barcode")
    @classmethod
    def validate_barcode(cls, value: str | None) -> str | None:
        if value is not None and not value.isdigit():
            raise ValueError("barcode must contain only digits")
        return value


class ProductCreate(ProductUpdate):
    product_code: str = Field(min_length=1, max_length=100)
    sku: str = Field(min_length=1, max_length=150)
    barcode: str = Field(min_length=8, max_length=14)
    sale_price: Decimal = Field(gt=0)
    desi: Decimal = Field(gt=0)


class ProductResponse(ToyProductFields):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_code: str
    sku: str
    barcode: str
    stock_quantity: int
    sale_price: Decimal
    attributes: dict[str, Any] = Field(default_factory=dict)