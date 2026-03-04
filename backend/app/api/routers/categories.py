import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.db.engine import get_db_session
from app.repositories.category_repository import CategoryRepository
from app.schemas.category import CategoryResponse
from app.services.category import CategoryService

router = APIRouter(prefix="/categories", tags=["categories"])


async def get_category_service(
    session=Depends(get_db_session),
) -> CategoryService:
    repository = CategoryRepository(session)
    return CategoryService(repository)


@router.get("", response_model=list[CategoryResponse])
async def list_categories(
    service: Annotated[CategoryService, Depends(get_category_service)]
):
    categories = await service.get_all_categories()
    return categories


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: uuid.UUID,
    service: Annotated[CategoryService, Depends(get_category_service)],
):
    category = await service.get_category(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.get("/slug/{slug}", response_model=CategoryResponse)
async def get_category_by_slug(
    slug: str,
    service: Annotated[CategoryService, Depends(get_category_service)],
):
    category = await service.get_category_by_slug(slug)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category
