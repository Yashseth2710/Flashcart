"""let people save products and mark sales to come back to

Revision ID: 0003_saved_and_reminders
Revises: 0002_product_media
Create Date: 2026-08-25 05:36:20.764870

Both tables record an intention rather than a claim. Neither holds stock, and
both go with the account that made them, so they cascade on delete instead of
having to be handed back the way a reservation is.

The unique pairs are what make saving twice the same as saving once: a second
tap on the button is answered rather than refused.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_saved_and_reminders"
down_revision: str | None = "0002_product_media"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "saved_products",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "product_id", name="uq_saved_user_product"),
    )
    op.create_index(
        op.f("ix_saved_products_product_id"), "saved_products", ["product_id"], unique=False
    )
    op.create_index(op.f("ix_saved_products_user_id"), "saved_products", ["user_id"], unique=False)

    op.create_table(
        "sale_reminders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("flash_sale_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["flash_sale_id"], ["flash_sales.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "flash_sale_id", name="uq_reminder_user_sale"),
    )
    op.create_index(
        op.f("ix_sale_reminders_flash_sale_id"), "sale_reminders", ["flash_sale_id"], unique=False
    )
    op.create_index(op.f("ix_sale_reminders_user_id"), "sale_reminders", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_sale_reminders_user_id"), table_name="sale_reminders")
    op.drop_index(op.f("ix_sale_reminders_flash_sale_id"), table_name="sale_reminders")
    op.drop_table("sale_reminders")

    op.drop_index(op.f("ix_saved_products_user_id"), table_name="saved_products")
    op.drop_index(op.f("ix_saved_products_product_id"), table_name="saved_products")
    op.drop_table("saved_products")
