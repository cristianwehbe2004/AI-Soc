from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260825_0005"
down_revision: str | None = "20260825_0004"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "model_registry" not in set(inspector.get_table_names()):
        op.create_table(
            "model_registry",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("model_name", sa.String(length=128), nullable=False),
            sa.Column("model_version", sa.String(length=255), nullable=False),
            sa.Column("algorithm", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("feature_version", sa.String(length=32), nullable=False),
            sa.Column("artifact_path", sa.String(length=1024), nullable=False),
            sa.Column("trained_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("evaluation_metrics", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("training_metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("model_version", name="uq_model_registry_version"),
        )

    inspector = sa.inspect(bind)
    indexes = {index["name"] for index in inspector.get_indexes("model_registry")}
    if op.f("ix_model_registry_model_name") not in indexes:
        op.create_index(op.f("ix_model_registry_model_name"), "model_registry", ["model_name"], unique=False)
    if op.f("ix_model_registry_status") not in indexes:
        op.create_index(op.f("ix_model_registry_status"), "model_registry", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_model_registry_status"), table_name="model_registry")
    op.drop_index(op.f("ix_model_registry_model_name"), table_name="model_registry")
    op.drop_table("model_registry")
