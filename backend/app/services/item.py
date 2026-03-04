from sqlalchemy.ext.asyncio import AsyncSession

# from app.models.item import Item
# from app.schemas.item import ItemCreate, ItemResponse


class ItemService:
    def __init__(self, session: AsyncSession):
        self.session = session

    # Placeholder for future business logic:
    # async def create_item(self, item_in: ItemCreate) -> ItemResponse:
    #     pass
    #
    # async def get_item(self, item_id: uuid.UUID) -> ItemResponse | None:
    #     pass
