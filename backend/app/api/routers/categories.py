import math
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response

from app.api.deps import require_admin
from app.db.engine import get_db_session
from app.repositories.category_repository import CategoryRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.category import (
    CategoryCreate,
    CategoryDetailResponse,
    CategoryResponse,
    CategoryUpdate,
    PaginatedCategoriesResponse,
)
from app.schemas.product import PaginatedProductsResponse
from app.services.category import CategoryConflictError, CategoryService
from app.services.product import ProductService

# ─── Shared DI ───────────────────────────────────────────────────────────────


async def get_category_service(
    session=Depends(get_db_session),
) -> CategoryService:
    repository = CategoryRepository(session)
    return CategoryService(repository)


async def get_product_service_for_categories(
    session=Depends(get_db_session),
) -> ProductService:
    product_repository = ProductRepository(session)
    category_repository = CategoryRepository(session)
    return ProductService(product_repository, category_repository)


# ─── Public Router ───────────────────────────────────────────────────────────

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=PaginatedCategoriesResponse)
async def list_categories(
    service: Annotated[CategoryService, Depends(get_category_service)],
    page: int = 1,
    size: int = 10,
):
    items, total = await service.list_active(page=page, size=size)
    pages = math.ceil(total / size) if size > 0 else 0
    return PaginatedCategoriesResponse(
        items=items, total=total, page=page, pages=pages, size=size
    )


@router.get("/{slug}", response_model=CategoryDetailResponse)
async def get_category_by_slug(
    slug: str,
    service: Annotated[CategoryService, Depends(get_category_service)],
    product_service: Annotated[ProductService, Depends(get_product_service_for_categories)],
    page: int = 1,
    size: int = 10,
):
    category = await service.get_active_by_slug(slug)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found.")

    # Fetch real products for this category
    products, total = await product_service.list_active(
        page=page,
        size=size,
        category_slug=slug,
        search=None,
        sort_by="name",
        sort_direction="asc",
    )
    pages = math.ceil(total / size) if size > 0 else 0
    products_response = PaginatedProductsResponse(
        items=products, total=total, page=page, pages=pages, size=size
    )
    return CategoryDetailResponse(category=category, products=products_response)


# ─── Admin Router ─────────────────────────────────────────────────────────────

admin_router = APIRouter(
    prefix="/admin/categories",
    tags=["admin", "categories"],
    dependencies=[Depends(require_admin)],
)


@admin_router.get("", response_model=PaginatedCategoriesResponse)
async def list_categories_admin(
    service: Annotated[CategoryService, Depends(get_category_service)],
    page: int = 1,
    size: int = 15,
):
    items, total = await service.list_all_admin(page=page, size=size)
    pages = math.ceil(total / size) if size > 0 else 0
    return PaginatedCategoriesResponse(
        items=items, total=total, page=page, pages=pages, size=size
    )


@admin_router.post("", response_model=CategoryResponse, status_code=201)
async def create_category(
    body: CategoryCreate,
    service: Annotated[CategoryService, Depends(get_category_service)],
):
    try:
        category = await service.create_category(
            name=body.name,
            slug=body.slug,
            description=body.description,
            image_path=body.image_path,
            is_active=body.is_active,
        )
    except CategoryConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return category


@admin_router.get("/{category_id}", response_model=CategoryResponse)
async def get_category_admin(
    category_id: int,
    service: Annotated[CategoryService, Depends(get_category_service)],
):
    category = await service.get_by_id(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found.")
    return category


@admin_router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int,
    body: CategoryUpdate,
    service: Annotated[CategoryService, Depends(get_category_service)],
):
    # Build a dict of only the fields that were explicitly provided
    data = body.model_dump(exclude_unset=True)
    try:
        category = await service.update_category(category_id, data)
    except CategoryConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if not category:
        raise HTTPException(status_code=404, detail="Category not found.")
    return category


@admin_router.delete("/{category_id}", status_code=204)
async def delete_category(
    category_id: int,
    service: Annotated[CategoryService, Depends(get_category_service)],
):
    deleted = await service.delete_category(category_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Category not found.")
    return Response(status_code=204)
