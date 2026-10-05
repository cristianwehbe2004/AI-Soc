from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "20261005_0011"
down_revision: str | None = "20261001_0010"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    op.add_column(
        "investigations",
        sa.Column("error_class", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "investigations",
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("investigations", "next_retry_at")
    op.drop_column("investigations", "error_class")
