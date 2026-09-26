import os
import uuid

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from .api.v1.hepsiburada import router as hepsiburada_router
from .db import Base, engine, ensure_sqlite_product_columns
from . import models  # noqa: F401
from .db import get_db
from .models import Product, ProductVariant
from .schemas import ProductCreate, ProductResponse, ProductUpdate

app = FastAPI(title="Toy Marketplace Integration API", version="1.0.0")
app.include_router(hepsiburada_router)


def _cors_origins() -> list[str]:
    configured = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    return [origin.strip() for origin in configured.split(",") if origin.strip()]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_sqlite_product_columns()


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/health", tags=["system"])
def api_health() -> dict[str, str]:
    return {"status": "ok"}


def _product_response(product: Product) -> ProductResponse:
    variant = next((item for item in product.variants if item.active), None)
    if variant is None:
        raise HTTPException(status_code=422, detail="Product must have an active variant")
    return ProductResponse(
        id=product.id,
        product_code=product.product_code,
        sku=variant.sku,
        barcode=variant.barcode,
        stock_quantity=variant.stock_quantity,
        sale_price=variant.sale_price,
        attributes=product.attributes,
        title=product.title,
        description=product.description,
        brand=product.brand,
        material=product.material,
        age_group=product.age_group,
        min_age_months=product.min_age_months,
        gender=product.gender,
        piece_count=product.piece_count,
        ce_compliant=product.ce_compliant,
        safety_warning=product.safety_warning,
    )


@app.get("/api/products", response_model=list[ProductResponse], tags=["products"])
def list_products(
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[ProductResponse]:
    products = db.scalars(select(Product).limit(limit)).all()
    return [_product_response(product) for product in products]


@app.post("/api/products", response_model=ProductResponse, status_code=201, tags=["products"])
def create_product(payload: ProductCreate, db: Session = Depends(get_db)) -> ProductResponse:
    product = Product(
        tenant_id=uuid.UUID(int=0),
        product_code=payload.product_code,
        title=payload.title,
        description=payload.description,
        brand=payload.brand,
        material=payload.material,
        age_group=payload.age_group,
        min_age_months=payload.min_age_months,
        gender=payload.gender,
        piece_count=payload.piece_count,
        ce_compliant=payload.ce_compliant,
        safety_warning=payload.safety_warning,
    )
    product.variants.append(
        ProductVariant(
            sku=payload.sku,
            barcode=payload.barcode,
            desi=payload.desi,
            stock_quantity=payload.stock_quantity or 0,
            sale_price=payload.sale_price,
        )
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return _product_response(product)


@app.put("/api/products/{product_id}", response_model=ProductResponse, tags=["products"])
def update_product(
    product_id: uuid.UUID,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
) -> ProductResponse:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    product_fields = payload.model_dump(exclude={"barcode", "sale_price", "stock_quantity"})
    for field_name, value in product_fields.items():
        setattr(product, field_name, value)
    variant = next((item for item in product.variants if item.active), None)
    if variant is None:
        raise HTTPException(status_code=422, detail="Product must have an active variant")
    if payload.barcode is not None:
        variant.barcode = payload.barcode
    if payload.sale_price is not None:
        variant.sale_price = payload.sale_price
    if payload.stock_quantity is not None:
        variant.stock_quantity = payload.stock_quantity
    db.commit()
    db.refresh(product)
    return _product_response(product)
