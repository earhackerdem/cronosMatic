from datetime import datetime

from pydantic import BaseModel, ConfigDict, computed_field

from app.config import settings


class CategoryBase(BaseModel):
    name: str
    slug: str
    description: str | None = None
    image_path: str | None = None
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class CategoryCreate(CategoryBase):
    """All base fields; name and slug are required (no default)."""

    pass


class CategoryUpdate(BaseModel):
    """Partial update — all fields optional."""

    name: str | None = None
    slug: str | None = None
    description: str | None = None
    image_path: str | None = None
    is_active: bool | None = None

    model_config = ConfigDict(from_attributes=True)


class CategoryResponse(CategoryBase):
    id: int
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def image_url(self) -> str | None:
        if self.image_path is None:
            return None
        if self.image_path.startswith("http"):
            return self.image_path
        base = settings.storage_base_url.rstrip("/")
        return f"{base}/{self.image_path}" if base else self.image_path


class PaginatedCategoriesResponse(BaseModel):
    items: list[CategoryResponse]
    total: int
    page: int
    pages: int
    size: int


class CategoryDetailResponse(BaseModel):
    from app.schemas.product import PaginatedProductsResponse as _PaginatedProductsResponse

    category: CategoryResponse
    products: _PaginatedProductsResponse
