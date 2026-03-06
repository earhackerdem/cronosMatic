"""replace slug unique constraint with partial unique index

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-05 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6g7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the old unique index on slug (covers all rows including soft-deleted)
    op.drop_index("ix_categories_slug", table_name="categories")
    # Create a partial unique index that only covers active (non-deleted) rows
    op.create_index(
        "uq_categories_slug_active",
        "categories",
        ["slug"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_categories_slug_active", table_name="categories")
    op.create_index("ix_categories_slug", "categories", ["slug"], unique=True)
