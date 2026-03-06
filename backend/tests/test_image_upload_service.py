"""Unit tests for ImageUploadService with mocked boto3."""

from unittest.mock import MagicMock, patch

import pytest

from app.services.image_upload import ImageUploadService, ImageUploadValidationError


def _make_settings(**overrides):
    settings = MagicMock()
    settings.aws_access_key_id = "AKIAIOSFODNN7EXAMPLE"
    settings.aws_secret_access_key = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    settings.aws_region = "us-east-1"
    settings.aws_s3_bucket = "test-bucket"
    settings.storage_base_url = "https://cdn.example.com"
    for k, v in overrides.items():
        setattr(settings, k, v)
    return settings


# ─── Validation tests ─────────────────────────────────────────────────────────


def test_upload_raises_on_invalid_mime_type():
    service = ImageUploadService(_make_settings())
    with pytest.raises(ImageUploadValidationError, match="mime"):
        service._validate("image/tiff", len(b"data"), b"data")


def test_upload_raises_on_file_too_large():
    service = ImageUploadService(_make_settings())
    large_content = b"x" * (5 * 1024 * 1024 + 1)
    with pytest.raises(ImageUploadValidationError, match="size"):
        service._validate("image/jpeg", len(large_content), large_content)


def test_upload_allows_valid_mime_types():
    service = ImageUploadService(_make_settings())
    for mime in ["image/jpeg", "image/png", "image/webp", "image/gif"]:
        # Should not raise
        service._validate(mime, 100, b"data")


# ─── Upload tests ─────────────────────────────────────────────────────────────


def test_upload_success_returns_path_and_url():
    settings = _make_settings()
    service = ImageUploadService(settings)

    mock_s3 = MagicMock()
    with patch("app.services.image_upload.boto3.client", return_value=mock_s3):
        result = service.upload(
            file_content=b"fake-image-data",
            content_type="image/jpeg",
            upload_type="products",
        )

    assert "path" in result
    assert "url" in result
    assert result["path"].startswith("products/")
    assert result["path"].endswith(".jpg")
    mock_s3.put_object.assert_called_once()


def test_upload_png_uses_correct_extension():
    settings = _make_settings()
    service = ImageUploadService(settings)

    mock_s3 = MagicMock()
    with patch("app.services.image_upload.boto3.client", return_value=mock_s3):
        result = service.upload(
            file_content=b"png-data",
            content_type="image/png",
            upload_type="categories",
        )

    assert result["path"].endswith(".png")
    assert result["path"].startswith("categories/")


def test_upload_generates_unique_paths():
    settings = _make_settings()
    service = ImageUploadService(settings)

    mock_s3 = MagicMock()
    with patch("app.services.image_upload.boto3.client", return_value=mock_s3):
        result1 = service.upload(b"data1", "image/jpeg", "products")
        result2 = service.upload(b"data2", "image/jpeg", "products")

    assert result1["path"] != result2["path"]


def test_upload_raises_validation_error_before_s3_call():
    settings = _make_settings()
    service = ImageUploadService(settings)

    mock_s3 = MagicMock()
    with patch("app.services.image_upload.boto3.client", return_value=mock_s3):
        with pytest.raises(ImageUploadValidationError):
            service.upload(b"data", "application/pdf", "products")

    mock_s3.put_object.assert_not_called()


def test_upload_url_uses_storage_base_url():
    settings = _make_settings(storage_base_url="https://cdn.example.com")
    service = ImageUploadService(settings)

    mock_s3 = MagicMock()
    with patch("app.services.image_upload.boto3.client", return_value=mock_s3):
        result = service.upload(b"data", "image/jpeg", "products")

    assert result["url"].startswith("https://cdn.example.com/")
