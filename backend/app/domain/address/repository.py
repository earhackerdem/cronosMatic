from typing import Protocol

from app.domain.address.entity import Address


class AddressRepositoryProtocol(Protocol):
    async def get_by_id(self, address_id: int) -> Address | None:
        """Retrieve an address by its ID."""
        ...

    async def get_by_user_id(
        self, user_id: int, type: str | None = None
    ) -> list[Address]:
        """Retrieve all addresses for a user, optionally filtered by type.

        Sorted by is_default DESC, created_at DESC.
        """
        ...

    async def create(self, address: Address) -> Address:
        """Persist a new address and return the domain entity."""
        ...

    async def update(self, address: Address) -> Address:
        """Update an existing address and return the updated domain entity."""
        ...

    async def delete(self, address_id: int) -> None:
        """Hard delete an address by its ID."""
        ...

    async def clear_defaults(self, user_id: int, type: str, exclude_id: int) -> None:
        """Set is_default=False for all addresses of user_id+type except exclude_id."""
        ...
