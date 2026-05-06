"""categories table and product category_id

Revision ID: 003
Revises: 002
Create Date: 2026-05-06
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    categories = op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.bulk_insert(categories, [
        {"name": "Açaí"},
        {"name": "Sorvete"},
        {"name": "Picolé"},
        {"name": "Outros"},
    ])

    op.add_column(
        "products",
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("categories.id"), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("products", "category_id")
    op.drop_table("categories")
