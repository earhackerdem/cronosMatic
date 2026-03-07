from datetime import datetime
from typing import Literal

from pydantic import BaseModel, computed_field


class AddressCreate(BaseModel):
    type: Literal["shipping", "billing"]
    first_name: str
    last_name: str
    company: str | None = None
    address_line_1: str
    address_line_2: str | None = None
    city: str
    state: str
    postal_code: str
    country: str
    phone: str | None = None
    is_default: bool = False


class AddressUpdate(BaseModel):
    type: Literal["shipping", "billing"] | None = None
    first_name: str | None = None
    last_name: str | None = None
    company: str | None = None
    address_line_1: str | None = None
    address_line_2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None
    phone: str | None = None
    is_default: bool | None = None


class AddressResponse(BaseModel):
    id: int
    type: str
    first_name: str
    last_name: str
    company: str | None
    address_line_1: str
    address_line_2: str | None
    city: str
    state: str
    postal_code: str
    country: str
    phone: str | None
    is_default: bool
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @computed_field
    @property
    def full_address(self) -> str:
        parts = [self.address_line_1]
        if self.address_line_2:
            parts.append(self.address_line_2)
        parts.append(f"{self.city}, {self.state} {self.postal_code}")
        parts.append(self.country)
        return ", ".join(parts)

    model_config = {"from_attributes": True}
