import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CategoryBase(BaseModel):
    name: dict[str, str] = Field(..., description="i18n category name")
    slug: str = Field(..., max_length=255, description="URL-friendly slug")
    description: dict[str, str] | None = Field(
        default=None, description="i18n category description"
    )

    model_config = ConfigDict(from_attributes=True)


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    """PATCH - all fields optional."""

    name: dict[str, str] | None = None
    slug: str | None = Field(default=None, max_length=255)
    description: dict[str, str] | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("name", "slug", mode="before")
    @classmethod
    def reject_null(cls, v: object, info: object) -> object:
        if v is None:
            raise ValueError(f"{info.field_name} cannot be null")
        return v


class CategoryResponse(CategoryBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
