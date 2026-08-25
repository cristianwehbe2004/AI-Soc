from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260825_0004"
down_revision: str | None = "20260825_0003"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "incidents" not in tables:
        op.create_table(
            "incidents",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("severity", sa.String(length=32), nullable=False),
            sa.Column("risk_score", sa.Integer(), nullable=False),
            sa.Column("primary_username", sa.String(length=255), nullable=True),
            sa.Column("primary_source_ip", sa.String(length=64), nullable=True),
            sa.Column("first_seen", sa.DateTime(timezone=True), nullable=False),
            sa.Column("last_seen", sa.DateTime(timezone=True), nullable=False),
            sa.Column(
                "timeline",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            ),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    incident_indexes = {index["name"] for index in inspector.get_indexes("incidents")} if "incidents" in set(inspector.get_table_names()) else set()
    for index_name, columns in [
        (op.f("ix_incidents_status"), ["status"]),
        (op.f("ix_incidents_severity"), ["severity"]),
        (op.f("ix_incidents_primary_username"), ["primary_username"]),
        (op.f("ix_incidents_primary_source_ip"), ["primary_source_ip"]),
        (op.f("ix_incidents_first_seen"), ["first_seen"]),
        (op.f("ix_incidents_last_seen"), ["last_seen"]),
    ]:
        if index_name not in incident_indexes:
            op.create_index(index_name, "incidents", columns, unique=False)

    if "incident_alerts" not in set(inspector.get_table_names()):
        op.create_table(
            "incident_alerts",
            sa.Column("incident_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("alert_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["alert_id"], ["alerts.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("incident_id", "alert_id"),
            sa.UniqueConstraint("incident_id", "alert_id", name="uq_incident_alert"),
        )


def downgrade() -> None:
    op.drop_table("incident_alerts")
    op.drop_index(op.f("ix_incidents_last_seen"), table_name="incidents")
    op.drop_index(op.f("ix_incidents_first_seen"), table_name="incidents")
    op.drop_index(op.f("ix_incidents_primary_source_ip"), table_name="incidents")
    op.drop_index(op.f("ix_incidents_primary_username"), table_name="incidents")
    op.drop_index(op.f("ix_incidents_severity"), table_name="incidents")
    op.drop_index(op.f("ix_incidents_status"), table_name="incidents")
    op.drop_table("incidents")
