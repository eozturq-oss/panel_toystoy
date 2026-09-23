from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Protocol

from PIL import Image, ImageOps


@dataclass(frozen=True)
class ImageProfile:
    width: int
    height: int
    format: str = "JPEG"
    quality: int = 90
    background: tuple[int, int, int] = (255, 255, 255)


IMAGE_PROFILES = {
    "TRENDYOL": ImageProfile(width=1200, height=1800),
    "HEPSIBURADA": ImageProfile(width=1200, height=1200),
}


@dataclass(frozen=True)
class ProcessedImage:
    content: bytes
    content_type: str
    width: int
    height: int
    extension: str


class PublicImageStorage(Protocol):
    def put(self, key: str, content: bytes, content_type: str) -> str:
        """Store bytes and return a URL reachable by marketplace servers."""
        ...


class ImageProcessingError(ValueError):
    pass


class ImageProcessor:
    def process(self, source: bytes, *, marketplace: str) -> ProcessedImage:
        profile = IMAGE_PROFILES.get(marketplace.upper())
        if profile is None:
            raise ImageProcessingError(f"unsupported marketplace image profile: {marketplace}")
        if not source:
            raise ImageProcessingError("image content cannot be empty")

        try:
            with Image.open(BytesIO(source)) as original:
                image = ImageOps.exif_transpose(original).convert("RGB")
                fitted = ImageOps.contain(image, (profile.width, profile.height), method=Image.Resampling.LANCZOS)
                canvas = Image.new("RGB", (profile.width, profile.height), profile.background)
                left = (profile.width - fitted.width) // 2
                top = (profile.height - fitted.height) // 2
                canvas.paste(fitted, (left, top))
                output = BytesIO()
                canvas.save(output, format=profile.format, quality=profile.quality, optimize=True)
        except (OSError, ValueError) as exc:
            raise ImageProcessingError("invalid or unsupported image") from exc

        return ProcessedImage(
            content=output.getvalue(),
            content_type="image/jpeg",
            width=profile.width,
            height=profile.height,
            extension="jpg",
        )


class LocalPublicImageStorage:
    """Stores images on a web-served directory and returns its public URL."""

    def __init__(self, root: str | Path, public_base_url: str) -> None:
        self.root = Path(root)
        self.public_base_url = public_base_url.rstrip("/")

    def put(self, key: str, content: bytes, content_type: str) -> str:
        safe_key = Path(key)
        if safe_key.is_absolute() or ".." in safe_key.parts:
            raise ValueError("image key must be a relative path")
        target = self.root / safe_key
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return f"{self.public_base_url}/{safe_key.as_posix()}"


class S3PublicImageStorage:
    """Uploads images to S3 or an S3-compatible object store."""

    def __init__(self, bucket: str, public_base_url: str, *, client=None) -> None:
        self.bucket = bucket
        self.public_base_url = public_base_url.rstrip("/")
        if client is None:
            try:
                import boto3
            except ImportError as exc:
                raise ImageProcessingError(
                    "boto3 is required to use S3PublicImageStorage"
                ) from exc
            client = boto3.client("s3")
        self.client = client

    def put(self, key: str, content: bytes, content_type: str) -> str:
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=content,
            ContentType=content_type,
            CacheControl="public, max-age=31536000, immutable",
        )
        return f"{self.public_base_url}/{key.lstrip('/')}"


class MarketplaceImageService:
    def __init__(self, storage: PublicImageStorage, processor: ImageProcessor | None = None) -> None:
        self.storage = storage
        self.processor = processor or ImageProcessor()

    def process_and_publish(self, source: bytes, *, key: str, marketplace: str) -> str:
        processed = self.processor.process(source, marketplace=marketplace)
        return self.storage.put(key, processed.content, processed.content_type)
