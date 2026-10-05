from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261005_0012"
down_revision: str | None = "20261005_0011"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    op.create_table(
        "response_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action_type", sa.String(64), nullable=False),
        sa.Column("target", sa.String(512), nullable=False),
        sa.Column("account_id", sa.String(32)),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("impact", sa.Text(), nullable=False),
        sa.Column("evidence_refs", postgresql.JSONB(), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("proposed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("result", postgresql.JSONB()),
        sa.Column("error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("incident_id", "idempotency_key", name="uq_response_action_idempotency"),
    )
    op.create_index("ix_response_actions_incident_created", "response_actions", ["incident_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_response_actions_incident_created", table_name="response_actions")
    op.drop_table("response_actions")
