from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260901_0008"
down_revision: str | None = "20260831_0007"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    op.create_table(
        "investigations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("context_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "context_snapshot",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("result", postgresql.JSONB(), nullable=True),
        sa.Column(
            "validation_errors",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "provider_response_ids",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "incident_id",
            "context_hash",
            "prompt_version",
            name="uq_investigation_context_version",
        ),
    )
    op.create_index(
        "ix_investigations_incident_id",
        "investigations",
        ["incident_id"],
        unique=False,
    )
    op.create_index(
        "ix_investigations_status",
        "investigations",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_investigations_incident_created",
        "investigations",
        ["incident_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_investigations_incident_created", table_name="investigations")
    op.drop_index("ix_investigations_status", table_name="investigations")
    op.drop_index("ix_investigations_incident_id", table_name="investigations")
    op.drop_table("investigations")
