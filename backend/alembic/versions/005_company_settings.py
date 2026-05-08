"""company_settings table

Revision ID: 005
Revises: 004
Create Date: 2026-05-08
"""
from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "company_settings",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("company_name", sa.String(128), nullable=False, server_default="SorvPel"),
        sa.Column("logo_path", sa.String(512), nullable=True),
        sa.Column("logo_icon", sa.String(64), nullable=False, server_default="bi-snow2"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.execute("INSERT INTO company_settings (company_name, logo_icon) VALUES ('SorvPel', 'bi-snow2')")


def downgrade():
    op.drop_table("company_settings")
