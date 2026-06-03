"""crear tabla products

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-03

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("stock", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("brand", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("category", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("image_url", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_products_name", "products", ["name"])
    op.create_index("ix_products_brand", "products", ["brand"])
    op.create_index("ix_products_category", "products", ["category"])


def downgrade() -> None:
    op.drop_index("ix_products_category", table_name="products")
    op.drop_index("ix_products_brand", table_name="products")
    op.drop_index("ix_products_name", table_name="products")
    op.drop_table("products")
