from __future__ import annotations

from enum import IntEnum, StrEnum
from pydantic import BaseModel, ConfigDict, Field


class ActionTier(IntEnum):
    TIER_0_AUTO = 0      # Non-disruptive: notification, enrich, snapshot
    TIER_1_LOW = 1       # Reversible/confined: temporary IP block (with TTL), session revocation
    TIER_2_MEDIUM = 2    # Disruptive: disable user, remove IAM role (Requires human approval)
    TIER_3_HIGH = 3      # High-impact/destructive: isolate host, wide network block (Multi-person or blocked)


class ActionType(StrEnum):
    NOTIFY = "notify"
    ENRICH_THREAT_INTEL = "enrich_threat_intel"
    SNAPSHOT_EVIDENCE = "snapshot_evidence"
    BLOCK_IP = "block_ip"
    REVOKE_SESSIONS = "revoke_sessions"
    DISABLE_USER = "disable_user"
    REMOVE_ROLE = "remove_role"
    ISOLATE_HOST = "isolate_host"


ACTION_TIERS: dict[ActionType, ActionTier] = {
    ActionType.NOTIFY: ActionTier.TIER_0_AUTO,
    ActionType.ENRICH_THREAT_INTEL: ActionTier.TIER_0_AUTO,
    ActionType.SNAPSHOT_EVIDENCE: ActionTier.TIER_0_AUTO,
    ActionType.BLOCK_IP: ActionTier.TIER_1_LOW,
    ActionType.REVOKE_SESSIONS: ActionTier.TIER_1_LOW,
    ActionType.DISABLE_USER: ActionTier.TIER_2_MEDIUM,
    ActionType.REMOVE_ROLE: ActionTier.TIER_2_MEDIUM,
    ActionType.ISOLATE_HOST: ActionTier.TIER_3_HIGH,
}


class ProposedAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_type: ActionType
    target: str = Field(min_length=1, max_length=256, description="Target identifier e.g. IP, email, username, UUID")
    reason: str = Field(min_length=5, max_length=500)
    evidence_refs: list[str] = Field(min_length=1, max_length=20)
    confidence: float = Field(ge=0.0, le=1.0)
    ttl_seconds: int | None = Field(default=None, ge=60, le=2592000, description="Time to live in seconds (e.g. 86400 for 24h IP block)")
    parameters: dict[str, str | int | float | bool] = Field(default_factory=dict)

    @property
    def tier(self) -> ActionTier:
        return ACTION_TIERS[self.action_type]


class ActionPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    incident_id: str
    actions: list[ProposedAction] = Field(default_factory=list, max_length=10)
