import uuid

from pydantic import BaseModel, ConfigDict, Field


class ItemBase(BaseModel):
    name: str = Field(..., max_length=255, description="Name of the item")
    embedding: list[float] | None = Field(
        default=None, description="Vector embedding representing the item"
    )


class ItemCreate(ItemBase):
    pass


class ItemResponse(ItemBase):
    id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)
