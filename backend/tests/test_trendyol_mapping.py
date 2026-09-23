from __future__ import annotations

import httpx
import pytest

from app.config import Settings
from app.integrations.trendyol import TrendyolClient
from app.integrations.trendyol_mapper import TrendyolCategoryMapper


@pytest.mark.asyncio
async def test_category_endpoints_use_trendyol_paths() -> None:
    requested_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        if request.url.path.endswith("/categories"):
            return httpx.Response(200, json={"categories": []})
        return httpx.Response(200, json={"categoryAttributes": []})

    settings = Settings(
        trendyol_supplier_id="123456",
        trendyol_api_key="api-key",
        trendyol_api_secret="api-secret",
        trendyol_base_url="https://example.test",
    )
    client = TrendyolClient(settings)
    await client._client.aclose()
    client._client = httpx.AsyncClient(
        base_url=settings.trendyol_base_url,
        transport=httpx.MockTransport(handler),
    )

    await client.get_categories()
    await client.get_category_attributes(987)
    await client.close()

    assert requested_paths == [
        "/suppliers/123456/v2/categories",
        "/suppliers/123456/v2/product-categories/987/attributes",
    ]


def test_maps_toy_category_age_group_and_gender() -> None:
    mapper = TrendyolCategoryMapper(
        category_aliases={
            "Legolar & Yapı Oyuncakları": ["Yapı Oyuncakları"],
        }
    )
    result = mapper.map_toy_category(
        local_category="Legolar & Yapı Oyuncakları",
        category_response={
            "categories": [
                {"id": 100, "name": "Oyuncaklar", "subCategories": [
                    {"id": 245, "name": "Yapı Oyuncakları"},
                ]}
            ]
        },
        attribute_response={
            "categoryAttributes": [
                {
                    "attributeId": 10,
                    "attributeName": "Yaş Grubu",
                    "attributeValues": [{"id": 101, "name": "3-6 Yaş"}],
                },
                {
                    "attributeId": 11,
                    "attributeName": "Cinsiyet",
                    "attributeValues": [{"id": 202, "name": "Unisex"}],
                },
            ]
        },
        product_attributes={"age_group": "3-6 Yaş", "gender": "Unisex"},
    )

    assert result == {
        "categoryId": 245,
        "attributes": [
            {"attributeId": 10, "attributeValueId": 101},
            {"attributeId": 11, "attributeValueId": 202},
        ],
    }
