import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response

from app.db.engine import get_db_session
from app.repositories.category_repository import CategoryRepository
from app.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate
from app.services.category import CategoryConflictError, CategoryService

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


@router.post("", response_model=CategoryResponse, status_code=201)
async def create_category(
    body: CategoryCreate,
    service: Annotated[CategoryService, Depends(get_category_service)],
):
    try:
        category = await service.create_category(
            name_i18n=body.name, slug=body.slug, description_i18n=body.description
        )
    except CategoryConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return category


@router.put("/{category_id}", response_model=CategoryResponse)
async def replace_category(
    category_id: uuid.UUID,
    body: CategoryCreate,
    service: Annotated[CategoryService, Depends(get_category_service)],
):
    try:
        category = await service.replace_category(
            category_id=category_id,
            name_i18n=body.name,
            slug=body.slug,
            description_i18n=body.description,
        )
    except CategoryConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.patch("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: uuid.UUID,
    body: CategoryUpdate,
    service: Annotated[CategoryService, Depends(get_category_service)],
):
    try:
        category = await service.update_category(category_id=category_id, data=body)
    except CategoryConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.delete("/{category_id}", status_code=204)
async def delete_category(
    category_id: uuid.UUID,
    service: Annotated[CategoryService, Depends(get_category_service)],
):
    deleted = await service.delete_category(category_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Category not found")
    return Response(status_code=204)
