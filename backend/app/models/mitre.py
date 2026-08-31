from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base import Base

json_type = JSON().with_variant(JSONB, "postgresql")


class MitreTechnique(Base):
    __tablename__ = "mitre_techniques"

    external_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str] = mapped_column(Text)
    tactics: Mapped[list[str]] = mapped_column(json_type, default=list)
    platforms: Mapped[list[str]] = mapped_column(json_type, default=list)
    version: Mapped[str] = mapped_column(String(32))
    source_url: Mapped[str] = mapped_column(String(512))
    is_subtechnique: Mapped[bool] = mapped_column(Boolean, default=False)
    parent_external_id: Mapped[str | None] = mapped_column(
        String(32),
        ForeignKey("mitre_techniques.external_id", ondelete="RESTRICT"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class RuleTechniqueMapping(Base):
    __tablename__ = "rule_technique_mappings"

    rule_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    technique_external_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("mitre_techniques.external_id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
