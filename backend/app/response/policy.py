from __future__ import annotations

import ipaddress
from dataclasses import dataclass, field
from typing import Any

from app.response.actions import ActionTier, ProposedAction
from app.response.circuit_breaker import CircuitBreaker


# Default protected entity targets that must NEVER be automated against
DEFAULT_PROTECTED_ENTITIES = frozenset({
    "admin",
    "root",
    "administrator",
    "soc_admin",
    "break_glass",
    "emergency_admin",
    "127.0.0.1",
    "::1",
    "localhost",
})

DEFAULT_PROTECTED_NETWORKS = (
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local / AWS metadata
)


@dataclass
class PolicyContext:
    incident_id: str
    incident_entities: set[str]
    valid_evidence_refs: set[str]
    protected_entities: set[str] = field(default_factory=lambda: set(DEFAULT_PROTECTED_ENTITIES))
    min_auto_confidence: float = 0.80


@dataclass
class PolicyDecision:
    allowed: bool
    requires_human_approval: bool
    reason: str
    action: ProposedAction


class PolicyEngine:
    """
    Deterministic security gate for all proposed response actions.
    No LLM is involved in this evaluation.
    """

    def __init__(self, circuit_breaker: CircuitBreaker | None = None) -> None:
        self.circuit_breaker = circuit_breaker or CircuitBreaker()

    async def evaluate(self, action: ProposedAction, context: PolicyContext) -> PolicyDecision:
        # 1. Global kill switch & circuit breaker check
        tripped, cb_reason = await self.circuit_breaker.is_tripped()
        if tripped:
            return PolicyDecision(
                allowed=False,
                requires_human_approval=False,
                reason=f"Circuit breaker tripped: {cb_reason}",
                action=action,
            )

        # 2. Target Grounding: Target entity MUST exist in incident entities
        normalized_target = action.target.strip().lower()
        if normalized_target not in {e.strip().lower() for e in context.incident_entities}:
            return PolicyDecision(
                allowed=False,
                requires_human_approval=False,
                reason=f"Ungrounded target '{action.target}' is not present in incident entities",
                action=action,
            )

        # 3. Protected Entity Check
        if normalized_target in {p.strip().lower() for p in context.protected_entities}:
            return PolicyDecision(
                allowed=False,
                requires_human_approval=False,
                reason=f"Target '{action.target}' is a protected entity (admin/service account/infrastructure)",
                action=action,
            )

        # 3b. IP Subnet / Loopback Check if target is an IP
        try:
            ip_obj = ipaddress.ip_address(action.target.strip())
            for net in DEFAULT_PROTECTED_NETWORKS:
                if ip_obj in net:
                    return PolicyDecision(
                        allowed=False,
                        requires_human_approval=False,
                        reason=f"Target IP '{action.target}' is within protected network {net}",
                        action=action,
                    )
        except ValueError:
            pass  # Not an IP address (e.g. username or UUID), continue

        # 4. Evidence Grounding: All cited evidence_refs must be a subset of valid_evidence_refs
        invalid_refs = set(action.evidence_refs) - set(context.valid_evidence_refs)
        if invalid_refs:
            return PolicyDecision(
                allowed=False,
                requires_human_approval=False,
                reason=f"Ungrounded evidence references cited: {sorted(invalid_refs)}",
                action=action,
            )

        # 5. Risk Tier & Human Approval Gate Evaluation
        tier = action.tier

        # Tier 3 (Isolate Host, Wide Destruction): Never auto-executed; requires manual approval or strict refusal
        if tier >= ActionTier.TIER_3_HIGH:
            return PolicyDecision(
                allowed=True,
                requires_human_approval=True,
                reason="Tier 3 high-impact action requires explicit human SOC analyst authorization",
                action=action,
            )

        # Tier 2 (Disable User, Remove Role): Always requires human approval
        if tier >= ActionTier.TIER_2_MEDIUM:
            return PolicyDecision(
                allowed=True,
                requires_human_approval=True,
                reason="Tier 2 disruptive action requires human analyst approval",
                action=action,
            )

        # Tier 1 (Block IP, Revoke Sessions): Auto-executed ONLY if confidence >= min_auto_confidence
        if tier == ActionTier.TIER_1_LOW:
            if action.confidence < context.min_auto_confidence:
                return PolicyDecision(
                    allowed=True,
                    requires_human_approval=True,
                    reason=f"Confidence {action.confidence:.2f} is below auto-execution threshold {context.min_auto_confidence:.2f}; deferred to human approval",
                    action=action,
                )
            return PolicyDecision(
                allowed=True,
                requires_human_approval=False,
                reason="Tier 1 action validated and approved for automated execution",
                action=action,
            )

        # Tier 0 (Notify, Enrich, Snapshot): Always allowed for auto-execution
        return PolicyDecision(
            allowed=True,
            requires_human_approval=False,
            reason="Tier 0 non-disruptive action approved for automated execution",
            action=action,
        )
