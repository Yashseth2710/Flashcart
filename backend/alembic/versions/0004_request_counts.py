"""count what each caller tries so one of them cannot take the sale

Revision ID: 0004_request_counts
Revises: 0003_saved_and_reminders
Create Date: 2026-08-25 18:20:11.402118

One row is one caller, one action, one minute. The unique triple is what makes
the tally correct under load: two requests arriving together both aim at the
same row, and the one that loses the race falls into an update rather than
inserting a second row and halving the count.

Nothing here protects stock. That is the row lock and the check constraint,
which hold whatever arrives. This only stops a single caller from spending a
whole sale's capacity on retries.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004_request_counts"
down_revision: str | None = "0003_saved_and_reminders"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "request_counts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("subject", sa.String(length=128), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("hits", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("subject", "action", "window_start", name="uq_count_subject_window"),
    )
    op.create_index(
        "ix_request_counts_window_start", "request_counts", ["window_start"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_request_counts_window_start", table_name="request_counts")
    op.drop_table("request_counts")
