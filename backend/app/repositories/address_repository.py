from sqlalchemy import update as sa_update, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.address.entity import Address
from app.domain.address.repository import AddressRepositoryProtocol
from app.models.address import AddressModel


class AddressRepository(AddressRepositoryProtocol):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ─── Mapping helpers ─────────────────────────────────────────────────────

    def _to_domain(self, model: AddressModel) -> Address:
        return Address(
            id=model.id,
            user_id=model.user_id,
            type=model.type,
            first_name=model.first_name,
            last_name=model.last_name,
            company=model.company,
            address_line_1=model.address_line_1,
            address_line_2=model.address_line_2,
            city=model.city,
            state=model.state,
            postal_code=model.postal_code,
            country=model.country,
            phone=model.phone,
            is_default=model.is_default,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, address: Address) -> AddressModel:
        return AddressModel(
            user_id=address.user_id,
            type=address.type,
            first_name=address.first_name,
            last_name=address.last_name,
            company=address.company,
            address_line_1=address.address_line_1,
            address_line_2=address.address_line_2,
            city=address.city,
            state=address.state,
            postal_code=address.postal_code,
            country=address.country,
            phone=address.phone,
            is_default=address.is_default,
        )

    # ─── Interface implementation ─────────────────────────────────────────────

    async def get_by_id(self, address_id: int) -> Address | None:
        result = await self.session.execute(
            select(AddressModel).where(AddressModel.id == address_id)
        )
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def get_by_user_id(
        self, user_id: int, type: str | None = None
    ) -> list[Address]:
        query = select(AddressModel).where(AddressModel.user_id == user_id)
        if type is not None:
            query = query.where(AddressModel.type == type)
        query = query.order_by(
            AddressModel.is_default.desc(), AddressModel.created_at.desc()
        )
        result = await self.session.execute(query)
        models = result.scalars().all()
        return [self._to_domain(m) for m in models]

    async def create(self, address: Address) -> Address:
        model = self._to_model(address)
        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return self._to_domain(model)

    async def update(self, address: Address) -> Address:
        result = await self.session.execute(
            select(AddressModel).where(AddressModel.id == address.id)
        )
        model = result.scalar_one()
        model.type = address.type
        model.first_name = address.first_name
        model.last_name = address.last_name
        model.company = address.company
        model.address_line_1 = address.address_line_1
        model.address_line_2 = address.address_line_2
        model.city = address.city
        model.state = address.state
        model.postal_code = address.postal_code
        model.country = address.country
        model.phone = address.phone
        model.is_default = address.is_default
        await self.session.commit()
        await self.session.refresh(model)
        return self._to_domain(model)

    async def delete(self, address_id: int) -> None:
        result = await self.session.execute(
            select(AddressModel).where(AddressModel.id == address_id)
        )
        model = result.scalar_one_or_none()
        if model:
            await self.session.delete(model)
            await self.session.commit()

    async def clear_defaults(self, user_id: int, type: str, exclude_id: int) -> None:
        await self.session.execute(
            sa_update(AddressModel)
            .where(
                AddressModel.user_id == user_id,
                AddressModel.type == type,
                AddressModel.id != exclude_id,
            )
            .values(is_default=False)
        )
        await self.session.commit()
