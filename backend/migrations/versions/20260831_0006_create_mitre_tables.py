from __future__ import annotations

from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260831_0006"
down_revision: str | None = "20260825_0005"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None

TECHNIQUES = [
    (
        "T1110",
        "Brute Force",
        "Adversaries may systematically guess passwords or crack password material "
        "to gain account access.",
        ["Credential Access"],
        [
            "Containers",
            "ESXi",
            "IaaS",
            "Identity Provider",
            "Linux",
            "Network Devices",
            "Office Suite",
            "SaaS",
            "Windows",
            "macOS",
        ],
        "2.8",
        "https://attack.mitre.org/techniques/T1110/",
        False,
        None,
    ),
    (
        "T1110.003",
        "Password Spraying",
        "Adversaries may try one or a small set of common passwords against many "
        "accounts.",
        ["Credential Access"],
        [
            "Containers",
            "ESXi",
            "IaaS",
            "Identity Provider",
            "Linux",
            "Network Devices",
            "Office Suite",
            "SaaS",
            "Windows",
            "macOS",
        ],
        "1.8",
        "https://attack.mitre.org/techniques/T1110/003/",
        True,
        "T1110",
    ),
    (
        "T1098",
        "Account Manipulation",
        "Adversaries may modify accounts, credentials, groups, or roles to preserve "
        "or elevate access.",
        ["Persistence", "Privilege Escalation"],
        [
            "Containers",
            "ESXi",
            "IaaS",
            "Identity Provider",
            "Linux",
            "Network Devices",
            "Office Suite",
            "SaaS",
            "Windows",
            "macOS",
        ],
        "2.8",
        "https://attack.mitre.org/techniques/T1098/",
        False,
        None,
    ),
    (
        "T1005",
        "Data from Local System",
        "Adversaries may collect sensitive data from local files, databases, "
        "configuration, or memory.",
        ["Collection"],
        ["ESXi", "Linux", "Network Devices", "Windows", "macOS"],
        "1.8",
        "https://attack.mitre.org/techniques/T1005/",
        False,
        None,
    ),
    (
        "T1078",
        "Valid Accounts",
        "Adversaries may abuse credentials for existing accounts to gain or "
        "maintain access.",
        ["Stealth", "Persistence", "Privilege Escalation", "Initial Access"],
        [
            "Containers",
            "ESXi",
            "IaaS",
            "Identity Provider",
            "Linux",
            "Network Devices",
            "Office Suite",
            "SaaS",
            "Windows",
            "macOS",
        ],
        "3.0",
        "https://attack.mitre.org/techniques/T1078/",
        False,
        None,
    ),
]

RULE_MAPPINGS = [
    ("rule_001_brute_force", "T1110"),
    ("rule_002_password_spray", "T1110.003"),
    ("rule_003_suspicious_privilege_change", "T1098"),
    ("rule_004_large_download", "T1005"),
    ("rule_005_login_after_failures", "T1078"),
]


def upgrade() -> None:
    op.create_table(
        "mitre_techniques",
        sa.Column("external_id", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("tactics", postgresql.JSONB(), nullable=False),
        sa.Column("platforms", postgresql.JSONB(), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("source_url", sa.String(length=512), nullable=False),
        sa.Column("is_subtechnique", sa.Boolean(), nullable=False),
        sa.Column("parent_external_id", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["parent_external_id"], ["mitre_techniques.external_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("external_id"),
    )
    op.create_index(op.f("ix_mitre_techniques_name"), "mitre_techniques", ["name"], unique=False)
    op.create_table(
        "rule_technique_mappings",
        sa.Column("rule_id", sa.String(length=128), nullable=False),
        sa.Column("technique_external_id", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["technique_external_id"], ["mitre_techniques.external_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("rule_id", "technique_external_id"),
    )
    now = datetime.now(UTC)
    technique_table = sa.table(
        "mitre_techniques",
        sa.column("external_id", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
        sa.column("tactics", postgresql.JSONB),
        sa.column("platforms", postgresql.JSONB),
        sa.column("version", sa.String),
        sa.column("source_url", sa.String),
        sa.column("is_subtechnique", sa.Boolean),
        sa.column("parent_external_id", sa.String),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    columns = [
        "external_id",
        "name",
        "description",
        "tactics",
        "platforms",
        "version",
        "source_url",
        "is_subtechnique",
        "parent_external_id",
    ]
    op.bulk_insert(
        technique_table,
        [dict(zip(columns, item), created_at=now, updated_at=now) for item in TECHNIQUES],
    )
    mapping_table = sa.table(
        "rule_technique_mappings",
        sa.column("rule_id", sa.String),
        sa.column("technique_external_id", sa.String),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(
        mapping_table,
        [
            {"rule_id": rule_id, "technique_external_id": technique_id, "created_at": now}
            for rule_id, technique_id in RULE_MAPPINGS
        ],
    )


def downgrade() -> None:
    op.drop_table("rule_technique_mappings")
    op.drop_index(op.f("ix_mitre_techniques_name"), table_name="mitre_techniques")
    op.drop_table("mitre_techniques")
