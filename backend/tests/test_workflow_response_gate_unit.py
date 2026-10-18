import uuid
import pytest
from app.investigation.state import InvestigationState
from app.investigation.workflow import InvestigationWorkflow
from app.response.actions import ActionType, ProposedAction


@pytest.mark.asyncio
async def test_workflow_policy_gate_and_execute_nodes():
    # Setup mock workflow state
    incident_id = str(uuid.uuid4())
    state: InvestigationState = {
        "incident_id": incident_id,
        "investigation_id": str(uuid.uuid4()),
        "context": type("MockContext", (), {
            "incident": {"primary_username": "victim_user", "primary_source_ip": "198.51.100.1"},
            "events": [{"username": "victim_user", "source_ip": "198.51.100.1"}],
            "valid_evidence_refs": ["alert:100"],
        })(),
        "recommendation_set": type("MockRecSet", (), {
            "action_plan": [
                # 1. Tier 1 with high confidence -> Auto-executed
                {
                    "action_type": "block_ip",
                    "target": "198.51.100.1",
                    "reason": "Attacker IP brute forcing credentials",
                    "evidence_refs": ["alert:100"],
                    "confidence": 0.95,
                    "ttl_seconds": 3600,
                },
                # 2. Tier 2 -> Deferred to human approval
                {
                    "action_type": "disable_user",
                    "target": "victim_user",
                    "reason": "User account takeover confirmed",
                    "evidence_refs": ["alert:100"],
                    "confidence": 0.99,
                },
                # 3. Ungrounded action -> Denied by policy
                {
                    "action_type": "block_ip",
                    "target": "203.0.113.99",
                    "reason": "Unrelated IP",
                    "evidence_refs": ["alert:100"],
                    "confidence": 0.9,
                },
            ]
        })(),
    }

    # Instantiate workflow helper
    workflow = InvestigationWorkflow.__new__(InvestigationWorkflow)
    workflow.session = None  # Mock session for unit check

    # 1. Run policy_gate_node
    gate_update = await workflow.policy_gate_node(state)
    decisions = gate_update["policy_decisions"]
    assert len(decisions) == 3

    # Decision 1: Allowed, no human approval needed
    assert decisions[0]["allowed"] is True
    assert decisions[0]["requires_human_approval"] is False

    # Decision 2: Allowed, but requires human approval
    assert decisions[1]["allowed"] is True
    assert decisions[1]["requires_human_approval"] is True

    # Decision 3: Rejected (ungrounded)
    assert decisions[2]["allowed"] is False
    assert "not present in incident entities" in decisions[2]["reason"]
