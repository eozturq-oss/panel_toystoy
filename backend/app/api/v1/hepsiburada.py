from __future__ import annotations

from collections.abc import AsyncIterator
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ...integrations.hepsiburada import HepsiburadaApiError
from ...services.hepsiburada_service import HepsiburadaService

router = APIRouter(
    prefix="/api/v1/hepsiburada",
    tags=["Hepsiburada"],
)


class HepsiburadaInventoryItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    merchant_sku: str = Field(alias="merchantSku", min_length=1)
    quantity: int = Field(ge=0)
    price: Decimal = Field(gt=0)


class HepsiburadaInventoryRequest(BaseModel):
    items: list[HepsiburadaInventoryItem] = Field(min_length=1)


class ToyAttributeRequest(BaseModel):
    category_id: str = Field(min_length=1)
    age_group: str = Field(min_length=1)
    gender: str = Field(min_length=1)
    ce_compliant: bool
    piece_count: int = Field(gt=0)
    material: str = Field(min_length=1)
    safety_warning: str | None = None
    extra_attributes: dict[str, Any] = Field(default_factory=dict)


async def get_hepsiburada_service() -> AsyncIterator[HepsiburadaService]:
    try:
        service = HepsiburadaService()
    except (ValueError, ValidationError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Hepsiburada credentials are not configured",
        ) from exc
    try:
        yield service
    finally:
        await service.close()


@router.get("/products", summary="List Hepsiburada products")
async def list_products(
    merchant_sku: str | None = Query(default=None, min_length=1),
    service: HepsiburadaService = Depends(get_hepsiburada_service),
) -> dict[str, Any]:
    try:
        return await service.list_products(merchant_sku=merchant_sku)
    except HepsiburadaApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/products", status_code=202, summary="Submit product listings")
async def create_products(
    payload: dict[str, Any],
    service: HepsiburadaService = Depends(get_hepsiburada_service),
) -> dict[str, str]:
    try:
        batch_id = await service.create_products(payload)
        return {"batch_id": batch_id}
    except HepsiburadaApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.put("/inventory", status_code=202, summary="Update merchant stock and price")
async def update_inventory(
    payload: HepsiburadaInventoryRequest,
    service: HepsiburadaService = Depends(get_hepsiburada_service),
) -> dict[str, str]:
    try:
        batch_id = await service.update_price_and_inventory(
            [item.model_dump(by_alias=True) for item in payload.items]
        )
        return {"batch_id": batch_id}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except HepsiburadaApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/categories", summary="List Hepsiburada categories")
async def get_categories(
    service: HepsiburadaService = Depends(get_hepsiburada_service),
) -> dict[str, Any]:
    try:
        return await service.get_categories()
    except HepsiburadaApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/categories/{category_id}/attributes", summary="List category attributes")
async def get_category_attributes(
    category_id: int,
    service: HepsiburadaService = Depends(get_hepsiburada_service),
) -> dict[str, Any]:
    try:
        return await service.get_category_attributes(category_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except HepsiburadaApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/toy-attributes", summary="Map required toy attributes")
async def map_toy_attributes(
    payload: ToyAttributeRequest,
    service: HepsiburadaService = Depends(get_hepsiburada_service),
) -> dict[str, Any]:
    try:
        return service.map_toy_attributes(
            category_id=payload.category_id,
            product=payload.model_dump(
                exclude={"category_id", "extra_attributes"},
                exclude_none=True,
            ),
            extra_attributes=payload.extra_attributes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc