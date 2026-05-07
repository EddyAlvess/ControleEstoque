"""operator pin_hash

Revision ID: 004
Revises: 003
Create Date: 2026-05-07
"""
from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("operators", sa.Column("pin_hash", sa.String(128), nullable=True))


def downgrade():
    op.drop_column("operators", "pin_hash")
