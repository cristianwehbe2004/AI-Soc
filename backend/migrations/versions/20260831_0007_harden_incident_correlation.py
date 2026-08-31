from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "20260831_0007"
down_revision: str | None = "20260831_0006"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    op.add_column(
        "incidents",
        sa.Column("correlation_key", sa.String(length=512), nullable=True),
    )
    op.execute(
        """
        UPDATE incidents
        SET correlation_key =
            'credential_compromise:u:' ||
            char_length(lower(btrim(coalesce(primary_username, '')))) || ':' ||
            lower(btrim(coalesce(primary_username, ''))) || '|s:' ||
            char_length(lower(btrim(coalesce(primary_source_ip, '')))) || ':' ||
            lower(btrim(coalesce(primary_source_ip, '')))
        """
    )
    op.alter_column("incidents", "correlation_key", nullable=False)
    op.create_index(
        "ix_incidents_correlation_lookup",
        "incidents",
        ["correlation_key", "status", "last_seen"],
        unique=False,
    )
    op.create_index(
        "ix_alerts_username_last_seen",
        "alerts",
        ["username", "last_seen"],
        unique=False,
    )
    op.create_index(
        "ix_alerts_source_ip_last_seen",
        "alerts",
        ["source_ip", "last_seen"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_alerts_source_ip_last_seen", table_name="alerts")
    op.drop_index("ix_alerts_username_last_seen", table_name="alerts")
    op.drop_index("ix_incidents_correlation_lookup", table_name="incidents")
    op.drop_column("incidents", "correlation_key")
