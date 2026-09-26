from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from datetime import datetime, timezone

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from .db import Base

JsonType = JSON().with_variant(JSONB, "postgresql")


def new_uuid() -> uuid.UUID:
    return uuid.uuid4()


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    product_code: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    brand: Mapped[str] = mapped_column(String(200), nullable=False)
    material: Mapped[str] = mapped_column(String(200), nullable=False)
    age_group: Mapped[str] = mapped_column(String(100), nullable=False)
    min_age_months: Mapped[int] = mapped_column(Integer, nullable=False)
    gender: Mapped[str] = mapped_column(String(50), nullable=False)
    license_character: Mapped[str | None] = mapped_column(String(200))
    piece_count: Mapped[int] = mapped_column(Integer, nullable=False)
    ce_compliant: Mapped[bool] = mapped_column(Boolean, nullable=False)
    vat_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("20.00"))
    safety_warning: Mapped[str] = mapped_column(Text, nullable=False, default="Uyarı belirtilmedi.")
    attributes: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict, nullable=False)

    variants: Mapped[list[ProductVariant]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    images: Mapped[list[ProductImage]] = relationship(
        back_populates="product", cascade="all, delete-orphan", order_by="ProductImage.sort_order"
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "product_code", name="uq_product_tenant_code"),
        CheckConstraint("min_age_months >= 0", name="ck_product_min_age_non_negative"),
        CheckConstraint("piece_count > 0", name="ck_product_piece_count_positive"),
    )


class ProductVariant(Base):
    __tablename__ = "product_variants"
    __table_args__ = (
        UniqueConstraint("product_id", "sku", name="uq_variant_product_sku"),
        UniqueConstraint("barcode", name="uq_variant_barcode"),
        CheckConstraint("desi > 0", name="ck_variant_desi_positive"),
        CheckConstraint("stock_quantity >= 0", name="ck_variant_stock_non_negative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    sku: Mapped[str] = mapped_column(String(150), nullable=False)
    barcode: Mapped[str] = mapped_column(String(14), nullable=False)
    variant_name: Mapped[str | None] = mapped_column(String(200))
    color: Mapped[str | None] = mapped_column(String(100))
    model: Mapped[str | None] = mapped_column(String(100))
    desi: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    stock_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sale_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    list_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    attributes: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    inventory_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    product: Mapped[Product] = relationship(back_populates="variants")
    listings: Mapped[list[MarketplaceListing]] = relationship(
        back_populates="variant", cascade="all, delete-orphan"
    )


class ProductImage(Base):
    __tablename__ = "product_images"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_main: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    product: Mapped[Product] = relationship(back_populates="images")


class Marketplace(Base):
    __tablename__ = "marketplaces"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    categories: Mapped[list[MarketplaceCategory]] = relationship(back_populates="marketplace")


class MarketplaceCategory(Base):
    __tablename__ = "marketplace_categories"
    __table_args__ = (UniqueConstraint("marketplace_id", "external_id", name="uq_marketplace_external_category"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    marketplace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("marketplaces.id"), nullable=False)
    external_id: Mapped[str] = mapped_column(String(150), nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    path: Mapped[str | None] = mapped_column(Text)
    required_attributes: Mapped[list[str]] = mapped_column(JsonType, default=list, nullable=False)
    attribute_schema: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict, nullable=False)

    marketplace: Mapped[Marketplace] = relationship(back_populates="categories")
    mappings: Mapped[list[CategoryMapping]] = relationship(back_populates="marketplace_category")


class CategoryMapping(Base):
    __tablename__ = "category_mappings"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "internal_category", "marketplace_category_id",
            name="uq_tenant_internal_marketplace_category",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    internal_category: Mapped[str] = mapped_column(String(200), nullable=False)
    marketplace_category_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("marketplace_categories.id"), nullable=False
    )
    attribute_mapping: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict, nullable=False)
    transformation_rules: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")

    marketplace_category: Mapped[MarketplaceCategory] = relationship(back_populates="mappings")


class MarketplaceListing(Base):
    __tablename__ = "marketplace_listings"
    __table_args__ = (UniqueConstraint("variant_id", "marketplace_id", name="uq_variant_marketplace_listing"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    variant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("product_variants.id"), nullable=False)
    marketplace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("marketplaces.id"), nullable=False)
    external_product_id: Mapped[str | None] = mapped_column(String(200))
    external_sku: Mapped[str | None] = mapped_column(String(200))
    listing_status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    inventory_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    variant: Mapped[ProductVariant] = relationship(back_populates="listings")


class TrendyolBatchRequest(Base):
    __tablename__ = "trendyol_batch_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    batch_request_id: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING")
    raw_response: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict, nullable=False)

    errors: Mapped[list[TrendyolBatchError]] = relationship(
        back_populates="batch", cascade="all, delete-orphan"
    )


class TrendyolBatchError(Base):
    __tablename__ = "trendyol_batch_errors"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    batch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("trendyol_batch_requests.id", ondelete="CASCADE"), nullable=False
    )
    barcode: Mapped[str | None] = mapped_column(String(14), index=True)
    stock_code: Mapped[str | None] = mapped_column(String(150), index=True)
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    raw_error: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict, nullable=False)

    batch: Mapped[TrendyolBatchRequest] = relationship(back_populates="errors")


class CustomerOrder(Base):
    __tablename__ = "customer_orders"
    __table_args__ = (
        UniqueConstraint("marketplace_code", "external_order_id", name="uq_marketplace_external_order"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    marketplace_code: Mapped[str] = mapped_column(String(50), nullable=False)
    external_order_id: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="RECEIVED")
    total_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    ordered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    items: Mapped[list[CustomerOrderItem]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class CustomerOrderItem(Base):
    __tablename__ = "customer_order_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customer_orders.id", ondelete="CASCADE"), nullable=False
    )
    barcode: Mapped[str] = mapped_column(String(14), nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    variant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("product_variants.id"))
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict, nullable=False)

    order: Mapped[CustomerOrder] = relationship(back_populates="items")


class MarketplaceOperationLog(Base):
    __tablename__ = "marketplace_operation_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    marketplace_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    operation: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    product_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("products.id"))
    variant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("product_variants.id"))
    barcode: Mapped[str | None] = mapped_column(String(14), index=True)
    batch_request_id: Mapped[str | None] = mapped_column(String(200), index=True)
    http_status: Mapped[int | None] = mapped_column(Integer)
    request_payload: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict, nullable=False)
    response_payload: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="INFO")
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    marketplace_code: Mapped[str | None] = mapped_column(String(50))
    product_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("products.id"))
    variant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("product_variants.id"))
    details: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
