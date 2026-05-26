"""Make hashed_password nullable for OAuth users

Revision ID: a1b2c3d4e5f6
Revises: fe56fa70289e
Create Date: 2026-05-25 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'fe56fa70289e'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('user', 'hashed_password',
               existing_type=sa.String(),
               nullable=True)


def downgrade():
    op.alter_column('user', 'hashed_password',
               existing_type=sa.String(),
               nullable=False)
