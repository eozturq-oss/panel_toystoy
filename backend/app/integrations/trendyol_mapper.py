from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any
import unicodedata


class TrendyolMappingError(ValueError):
    """Raised when local toy data cannot be mapped to Trendyol metadata."""


DEFAULT_ATTRIBUTE_ALIASES: dict[str, tuple[str, ...]] = {
    "age_group": ("Yaş Grubu", "Minimum Yaş", "Yaş"),
    "gender": ("Cinsiyet",),
    "material": ("Materyal", "Malzeme"),
    "ce_compliant": ("CE Uygunluk", "CE Belgesi", "CE"),
    "safety_warning": ("Uyarı Metni", "Uyarılar", "Güvenlik Uyarısı"),
}


class TrendyolCategoryMapper:
    def __init__(
        self,
        *,
        category_aliases: Mapping[str, Iterable[str]] | None = None,
        attribute_aliases: Mapping[str, Iterable[str]] | None = None,
    ) -> None:
        self.category_aliases = {
            _normalize(key): tuple(values)
            for key, values in (category_aliases or {}).items()
        }
        self.attribute_aliases = {
            **DEFAULT_ATTRIBUTE_ALIASES,
            **(attribute_aliases or {}),
        }

    def map_toy_category(
        self,
        *,
        local_category: str,
        category_response: Mapping[str, Any],
        attribute_response: Mapping[str, Any],
        product_attributes: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Build the categoryId/attributes payload expected by Trendyol."""
        category = self._find_category(local_category, category_response)
        category_id = _read_id(category, "categoryId", "id")
        if category_id is None:
            raise TrendyolMappingError(f"Category '{local_category}' has no category ID")

        definitions = _read_list(attribute_response, "categoryAttributes", "attributes")
        mapped_attributes: list[dict[str, int]] = []
        for field_name, field_value in product_attributes.items():
            if field_value is None or field_value == "":
                continue
            definition = self._find_attribute_definition(field_name, definitions)
            if definition is None:
                raise TrendyolMappingError(
                    f"No Trendyol attribute definition found for local field '{field_name}'"
                )
            attribute_id = _read_id(definition, "attributeId", "id")
            value_id = self._find_value_id(definition, field_value)
            if attribute_id is None or value_id is None:
                raise TrendyolMappingError(
                    f"Value '{field_value}' cannot be mapped for '{field_name}'"
                )
            mapped_attributes.append(
                {"attributeId": attribute_id, "attributeValueId": value_id}
            )

        return {"categoryId": category_id, "attributes": mapped_attributes}

    def _find_category(
        self, local_category: str, category_response: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        candidates = self.category_aliases.get(_normalize(local_category), (local_category,))
        for category in _flatten_categories(category_response):
            category_name = str(category.get("name", category.get("categoryName", "")))
            if any(_normalize(candidate) == _normalize(category_name) for candidate in candidates):
                return category
        raise TrendyolMappingError(f"Trendyol category not found for '{local_category}'")

    def _find_attribute_definition(
        self, field_name: str, definitions: list[Mapping[str, Any]]
    ) -> Mapping[str, Any] | None:
        aliases = self.attribute_aliases.get(field_name, (field_name,))
        for definition in definitions:
            name = str(definition.get("attributeName", definition.get("name", "")))
            if any(_normalize(alias) == _normalize(name) for alias in aliases):
                return definition
        return None

    def _find_value_id(self, definition: Mapping[str, Any], value: Any) -> int | None:
        values = _read_list(definition, "attributeValues", "values")
        requested = _normalize(str(value))
        for candidate in values:
            candidate_name = str(candidate.get("name", candidate.get("value", "")))
            if requested == _normalize(candidate_name):
                return _read_id(candidate, "id", "attributeValueId")
        return None


def map_toy_category(
    local_category: str,
    category_response: Mapping[str, Any],
    attribute_response: Mapping[str, Any],
    product_attributes: Mapping[str, Any],
    *,
    category_aliases: Mapping[str, Iterable[str]] | None = None,
) -> dict[str, Any]:
    """Convenience wrapper for mapping a toy category and dynamic attributes."""
    mapper = TrendyolCategoryMapper(category_aliases=category_aliases)
    return mapper.map_toy_category(
        local_category=local_category,
        category_response=category_response,
        attribute_response=attribute_response,
        product_attributes=product_attributes,
    )


def _flatten_categories(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    result: list[Mapping[str, Any]] = []

    def visit(value: Any) -> None:
        if isinstance(value, list):
            for item in value:
                visit(item)
            return
        if not isinstance(value, Mapping):
            return
        if "id" in value or "categoryId" in value:
            result.append(value)
        for key in ("categories", "subCategories", "children"):
            visit(value.get(key))

    visit(payload)
    return result


def _read_list(payload: Mapping[str, Any], *keys: str) -> list[Mapping[str, Any]]:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, Mapping)]
    return []


def _read_id(payload: Mapping[str, Any], *keys: str) -> int | None:
    for key in keys:
        value = payload.get(key)
        if value is not None:
            try:
                return int(value)
            except (TypeError, ValueError):
                return None
    return None


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    return "".join(character for character in normalized if character.isalnum())
