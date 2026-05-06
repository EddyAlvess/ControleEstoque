"""shifts table

Revision ID: 002
Revises: 001
Create Date: 2026-05-06
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    shifts = op.create_table(
        "shifts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(32), nullable=False),
        sa.Column("label", sa.String(64), nullable=False),
        sa.Column("start_hour", sa.Integer(), nullable=False),
        sa.Column("end_hour", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.bulk_insert(shifts, [
        {"name": "MANHA", "label": "Manhã",  "start_hour": 6,  "end_hour": 14, "is_active": True},
        {"name": "TARDE", "label": "Tarde",  "start_hour": 14, "end_hour": 22, "is_active": True},
        {"name": "NOITE", "label": "Noite",  "start_hour": 22, "end_hour": 6,  "is_active": True},
    ])


def downgrade() -> None:
    op.drop_table("shifts")
