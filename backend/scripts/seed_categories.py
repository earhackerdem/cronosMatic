import asyncio

from app.db.engine import async_session_factory
from app.repositories.category_repository import CategoryRepository
from app.services.category import CategoryService


async def seed_categories() -> None:
    async with async_session_factory() as session:
        repository = CategoryRepository(session)
        service = CategoryService(repository)

        initial_categories = [
            {
                "slug": "pocket",
                "name": {"es": "Bolsillo", "en": "Pocket"},
                "description": {
                    "es": "Relojes clásicos de bolsillo.",
                    "en": "Classic pocket watches.",
                },
            },
            {
                "slug": "wrist",
                "name": {"es": "Pulsera", "en": "Wrist"},
                "description": {
                    "es": "Relojes modernos y elegantes de pulsera.",
                    "en": "Modern and elegant wristwatches.",
                },
            },
            {
                "slug": "wall",
                "name": {"es": "Pared", "en": "Wall"},
                "description": {
                    "es": "Relojes decorativos de pared.",
                    "en": "Decorative wall clocks.",
                },
            },
        ]

        print("Seeding categories...")
        for cat_data in initial_categories:
            existing = await service.get_category_by_slug(cat_data["slug"])
            if not existing:
                await service.create_category(
                    slug=cat_data["slug"],
                    name_i18n=cat_data["name"],
                    description_i18n=cat_data["description"],
                )
                print(f"✅ Created category: {cat_data['slug']}")
            else:
                print(f"⚡ Skipped category (already exists): {cat_data['slug']}")
        print("Seeding completed.")


if __name__ == "__main__":
    asyncio.run(seed_categories())
