from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class HepsiburadaMappingError(ValueError):
    """Raised when toy attributes cannot be mapped to Hepsiburada format."""


DEFAULT_TOY_ATTRIBUTE_NAMES = {
    "age_group": "Yaş Grubu",
    "gender": "Cinsiyet",
    "ce_compliant": "CE Sertifika Bilgisi",
    "piece_count": "Parça Sayısı",
    "material": "Materyal",
    "safety_warning": "Uyarı Metni",
}


class HepsiburadaToyMapper:
    def __init__(self, attribute_names: Mapping[str, str] | None = None) -> None:
        self.attribute_names = {**DEFAULT_TOY_ATTRIBUTE_NAMES, **(attribute_names or {})}

    def map_product_attributes(
        self,
        *,
        category_id: str,
        product: Mapping[str, Any],
        extra_attributes: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build Hepsiburada's category and name/value attribute payload."""
        if not str(category_id).strip():
            raise HepsiburadaMappingError("category_id is required")

        values = {
            "age_group": product.get("age_group"),
            "gender": product.get("gender"),
            "ce_compliant": _ce_value(product.get("ce_compliant")),
            "piece_count": product.get("piece_count"),
            "material": product.get("material"),
        }
        if "safety_warning" in product:
            values["safety_warning"] = product.get("safety_warning")
        if extra_attributes:
            values.update(extra_attributes)

        attributes: list[dict[str, str]] = []
        for field_name, value in values.items():
            if value is None or value == "":
                raise HepsiburadaMappingError(
                    f"required toy attribute '{field_name}' is missing"
                )
            attributes.append(
                {
                    "name": self.attribute_names.get(field_name, field_name),
                    "value": str(value),
                }
            )

        return {"categoryId": str(category_id), "attributes": attributes}


def map_toy_attributes(
    *,
    category_id: str,
    age_group: str,
    gender: str,
    ce_compliant: bool,
    piece_count: int,
    material: str,
) -> dict[str, Any]:
    """Convenience function for the required toy fields."""
    return HepsiburadaToyMapper().map_product_attributes(
        category_id=category_id,
        product={
            "age_group": age_group,
            "gender": gender,
            "ce_compliant": ce_compliant,
            "piece_count": piece_count,
            "material": material,
        },
    )


def _ce_value(value: Any) -> str | None:
    if value is None:
        return None
    return "Evet" if bool(value) else "Hayır"
