from app.domain.address.entity import Address
from app.domain.address.exceptions import AddressNotFoundError
from app.domain.address.repository import AddressRepositoryProtocol


class AddressService:
    def __init__(self, repository: AddressRepositoryProtocol) -> None:
        self.repository = repository

    async def list_addresses(
        self, user_id: int, type: str | None = None
    ) -> list[Address]:
        return await self.repository.get_by_user_id(user_id, type=type)

    async def get_address(self, user_id: int, address_id: int) -> Address:
        address = await self.repository.get_by_id(address_id)
        if not address or address.user_id != user_id:
            raise AddressNotFoundError(f"Address {address_id} not found.")
        return address

    async def create_address(self, user_id: int, data: dict) -> Address:
        address = Address(
            user_id=user_id,
            type=data["type"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            company=data.get("company"),
            address_line_1=data["address_line_1"],
            address_line_2=data.get("address_line_2"),
            city=data["city"],
            state=data["state"],
            postal_code=data["postal_code"],
            country=data["country"],
            phone=data.get("phone"),
            is_default=data.get("is_default", False),
        )
        created = await self.repository.create(address)
        if created.is_default and created.id is not None:
            await self.repository.clear_defaults(
                user_id=user_id,
                type=created.type,
                exclude_id=created.id,
            )
        return created

    async def update_address(
        self, user_id: int, address_id: int, data: dict
    ) -> Address:
        address = await self.get_address(user_id, address_id)

        # Apply only the fields that were provided
        for field in (
            "type",
            "first_name",
            "last_name",
            "company",
            "address_line_1",
            "address_line_2",
            "city",
            "state",
            "postal_code",
            "country",
            "phone",
            "is_default",
        ):
            if field in data:
                setattr(address, field, data[field])

        updated = await self.repository.update(address)
        if updated.is_default and updated.id is not None:
            await self.repository.clear_defaults(
                user_id=user_id,
                type=updated.type,
                exclude_id=updated.id,
            )
        return updated

    async def delete_address(self, user_id: int, address_id: int) -> None:
        await self.get_address(user_id, address_id)
        await self.repository.delete(address_id)

    async def set_default(self, user_id: int, address_id: int) -> Address:
        address = await self.get_address(user_id, address_id)
        address.is_default = True
        updated = await self.repository.update(address)
        await self.repository.clear_defaults(
            user_id=user_id,
            type=updated.type,
            exclude_id=updated.id,
        )
        return updated
