"""Create events table."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260824_0002"
down_revision: str | None = "20260824_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("event_id", sa.String(length=128), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=True),
        sa.Column("user_id", sa.String(length=128), nullable=True),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("source_ip", sa.String(length=64), nullable=True),
        sa.Column("destination_ip", sa.String(length=64), nullable=True),
        sa.Column("source_port", sa.Integer(), nullable=True),
        sa.Column("destination_port", sa.Integer(), nullable=True),
        sa.Column("hostname", sa.String(length=255), nullable=True),
        sa.Column("device_id", sa.String(length=255), nullable=True),
        sa.Column("action", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=True),
        sa.Column("resource", sa.String(length=255), nullable=True),
        sa.Column("resource_type", sa.String(length=128), nullable=True),
        sa.Column("country", sa.String(length=128), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("bytes_sent", sa.Integer(), nullable=True),
        sa.Column("bytes_received", sa.Integer(), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id"),
    )
    op.create_index(op.f("ix_events_category"), "events", ["category"], unique=False)
    op.create_index(op.f("ix_events_event_id"), "events", ["event_id"], unique=False)
    op.create_index(op.f("ix_events_event_type"), "events", ["event_type"], unique=False)
    op.create_index(op.f("ix_events_severity"), "events", ["severity"], unique=False)
    op.create_index(op.f("ix_events_source"), "events", ["source"], unique=False)
    op.create_index(op.f("ix_events_source_ip"), "events", ["source_ip"], unique=False)
    op.create_index(op.f("ix_events_timestamp"), "events", ["timestamp"], unique=False)
    op.create_index(op.f("ix_events_username"), "events", ["username"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_events_username"), table_name="events")
    op.drop_index(op.f("ix_events_timestamp"), table_name="events")
    op.drop_index(op.f("ix_events_source_ip"), table_name="events")
    op.drop_index(op.f("ix_events_source"), table_name="events")
    op.drop_index(op.f("ix_events_severity"), table_name="events")
    op.drop_index(op.f("ix_events_event_type"), table_name="events")
    op.drop_index(op.f("ix_events_event_id"), table_name="events")
    op.drop_index(op.f("ix_events_category"), table_name="events")
    op.drop_table("events")
