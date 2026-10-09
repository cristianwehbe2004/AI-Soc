"""Add analyst-supplied, bounded incident evidence."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261006_0014"
down_revision: str | None = "20261005_0013"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    op.create_table(
        "incident_evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("submitted_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("kind", sa.String(48), nullable=False),
        sa.Column("source", sa.String(160), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("network", postgresql.JSONB()),
        sa.Column("observed_at", sa.DateTime(timezone=True)),
        sa.Column("sensitive_redacted", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_incident_evidence_incident_created", "incident_evidence", ["incident_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_incident_evidence_incident_created", table_name="incident_evidence")
    op.drop_table("incident_evidence")
