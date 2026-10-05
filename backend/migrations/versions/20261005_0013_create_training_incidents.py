"""Create isolated training-only incident examples."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261005_0013"
down_revision: str | None = "20261005_0012"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    op.create_table(
        "training_incidents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scenario_id", sa.String(160), nullable=False, unique=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("account_id", sa.String(128), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True)),
        sa.Column("source_kind", sa.String(64), nullable=False),
        sa.Column("review_status", sa.String(32), nullable=False),
        sa.Column("labels", postgresql.JSONB(), nullable=False),
        sa.Column("events", postgresql.JSONB(), nullable=False),
        sa.Column("source_ref", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_training_incidents_source_review", "training_incidents", ["source_kind", "review_status"])


def downgrade() -> None:
    op.drop_index("ix_training_incidents_source_review", table_name="training_incidents")
    op.drop_table("training_incidents")
