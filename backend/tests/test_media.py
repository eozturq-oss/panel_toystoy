from __future__ import annotations

from io import BytesIO

from PIL import Image
import pytest

from app.media import (
    ImageProcessingError,
    ImageProcessor,
    LocalPublicImageStorage,
    MarketplaceImageService,
)


def image_bytes(width: int = 400, height: int = 200) -> bytes:
    image = Image.new("RGB", (width, height), (220, 100, 50))
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def test_trendyol_image_is_padded_to_vertical_jpeg_profile() -> None:
    processed = ImageProcessor().process(image_bytes(), marketplace="trendyol")

    assert processed.width == 1200
    assert processed.height == 1800
    assert processed.content_type == "image/jpeg"
    with Image.open(BytesIO(processed.content)) as result:
        assert result.format == "JPEG"
        assert result.size == (1200, 1800)


def test_service_publishes_processed_image_with_public_url(tmp_path) -> None:
    storage = LocalPublicImageStorage(tmp_path, "https://cdn.example.test/toys")
    url = MarketplaceImageService(storage).process_and_publish(
        image_bytes(), key="product-1/main.jpg", marketplace="HEPSIBURADA"
    )

    assert url == "https://cdn.example.test/toys/product-1/main.jpg"
    with Image.open(tmp_path / "product-1" / "main.jpg") as result:
        assert result.size == (1200, 1200)
        assert result.format == "JPEG"


def test_rejects_invalid_image() -> None:
    with pytest.raises(ImageProcessingError):
        ImageProcessor().process(b"not an image", marketplace="TRENDYOL")
