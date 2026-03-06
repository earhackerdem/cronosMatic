import uuid

import boto3

from app.config import Settings

ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_SIZE_BYTES = 5 * 1024 * 1024  # 5MB

_MIME_TO_EXT = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
}


class ImageUploadValidationError(ValueError):
    """Raised when an uploaded image fails validation."""


class ImageUploadService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def _validate(
        self, content_type: str, content_length: int, file_content: bytes
    ) -> None:
        if content_type not in ALLOWED_MIME_TYPES:
            raise ImageUploadValidationError(
                f"Invalid mime type '{content_type}'. Allowed types: {', '.join(sorted(ALLOWED_MIME_TYPES))}."
            )
        if content_length > MAX_SIZE_BYTES:
            raise ImageUploadValidationError(
                f"File size {content_length} exceeds maximum allowed size of {MAX_SIZE_BYTES} bytes."
            )

    def upload(
        self,
        file_content: bytes,
        content_type: str,
        upload_type: str,
    ) -> dict[str, str]:
        """Validate and upload file to S3. Returns dict with 'path' and 'url'."""
        self._validate(content_type, len(file_content), file_content)

        extension = _MIME_TO_EXT[content_type]
        filename = f"{uuid.uuid4()}.{extension}"
        path = f"{upload_type}/{filename}"

        s3 = boto3.client(
            "s3",
            region_name=self.settings.aws_region,
            aws_access_key_id=self.settings.aws_access_key_id,
            aws_secret_access_key=self.settings.aws_secret_access_key,
        )
        s3.put_object(
            Bucket=self.settings.aws_s3_bucket,
            Key=path,
            Body=file_content,
            ContentType=content_type,
        )

        base = self.settings.storage_base_url.rstrip("/")
        url = f"{base}/{path}" if base else path

        return {"path": path, "url": url}
