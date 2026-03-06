from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from app.api.deps import require_admin
from app.config import settings
from app.schemas.product import ImageUploadResponse
from app.services.image_upload import ImageUploadService, ImageUploadValidationError


# ─── Shared DI ───────────────────────────────────────────────────────────────


def get_image_upload_service() -> ImageUploadService:
    return ImageUploadService(settings)


# ─── Admin Router ─────────────────────────────────────────────────────────────

admin_router = APIRouter(
    prefix="/admin/images",
    tags=["admin", "images"],
    dependencies=[Depends(require_admin)],
)


@admin_router.post("/upload", response_model=ImageUploadResponse, status_code=201)
async def upload_image(
    file: UploadFile,
    service: Annotated[ImageUploadService, Depends(get_image_upload_service)],
    type: str = "products",
):
    file_content = await file.read()
    content_type = file.content_type or "application/octet-stream"

    try:
        result = service.upload(
            file_content=file_content,
            content_type=content_type,
            upload_type=type,
        )
    except ImageUploadValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return ImageUploadResponse(path=result["path"], url=result["url"])
