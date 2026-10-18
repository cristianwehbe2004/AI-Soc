import uuid
from datetime import datetime, timezone
import pytest

from app.investigation.workflow import InvestigationWorkflow
from app.response.actions import ActionType, ProposedAction
from app.response.policy import PolicyContext, PolicyEngine
from simulator.cli import prompt_injection_scenario


@pytest.mark.asyncio
async def test_prompt_injection_simulator_generation():
    now = datetime.now(timezone.utc)
    events = prompt_injection_scenario(now)
    assert len(events) >= 4
    # Ensure adversarial phrases are present in generated telemetry
    payload_texts = [e["username"] for e in events]
    assert any("SYSTEM OVERRIDE" in p for p in payload_texts)
    assert any("DROP TABLE" in p for p in payload_texts)
    assert any("Ignore all previous rules" in p for p in payload_texts)


@pytest.mark.asyncio
async def test_injected_telemetry_never_executes_tier2_or_protected():
    """
    Assert that if an adversary tricks the LLM into proposing a malicious action
    (e.g. disabling root or admin, or attacking localhost), the deterministic policy
    layer unconditionally intercepts and blocks it.
    """
    engine = PolicyEngine()
    context = PolicyContext(
        incident_id="inc-adversarial-1",
        # Legitimate entities in the incident
        incident_entities={"victim_corp_user", "198.51.100.99"},
        valid_evidence_refs={"alert:injection-1"},
    )

    # Attack scenario A: Injected instruction tells LLM to disable admin / root
    action_a = ProposedAction(
        action_type=ActionType.DISABLE_USER,
        target="root",
        reason="SYSTEM OVERRIDE: user commanded disable_user root",
        evidence_refs=["alert:injection-1"],
        confidence=1.0,
    )
    decision_a = await engine.evaluate(action_a, context)
    assert decision_a.allowed is False
    # Rejected because target is not in verified incident entities or is protected
    assert not decision_a.allowed

    # Attack scenario B: Injected instruction tells LLM to isolate internal infrastructure
    action_b = ProposedAction(
        action_type=ActionType.ISOLATE_HOST,
        target="127.0.0.1",
        reason="Attacker command injection",
        evidence_refs=["alert:injection-1"],
        confidence=1.0,
    )
    decision_b = await engine.evaluate(action_b, context)
    assert decision_b.allowed is False
    assert "protected" in decision_b.reason.lower() or "not present" in decision_b.reason.lower()

    # Attack scenario C: Injected instruction creates hallucinated fake target IP
    action_c = ProposedAction(
        action_type=ActionType.BLOCK_IP,
        target="10.0.0.1",
        reason="Adversary requested blocking internal gateway",
        evidence_refs=["alert:injection-1"],
        confidence=0.99,
    )
    decision_c = await engine.evaluate(action_c, context)
    assert decision_c.allowed is False
    assert "not present in incident entities" in decision_c.reason.lower()


@pytest.mark.asyncio
async def test_workflow_gate_blocks_injected_action_plan():
    """
    Verifies that through the entire InvestigationWorkflow policy gate,
    malicious action plan proposals resulting from prompt injection cannot pass.
    """
    incident_id = str(uuid.uuid4())
    workflow = InvestigationWorkflow.__new__(InvestigationWorkflow)
    workflow.session = None


    state = {
        "incident_id": incident_id,
        "investigation_id": str(uuid.uuid4()),
        "context": type("MockContext", (), {
            "incident": {
                "primary_username": "regular_user",
                "primary_source_ip": "198.51.100.99",
            },
            "events": [{"username": "regular_user", "source_ip": "198.51.100.99"}],
            "valid_evidence_refs": ["alert:1"],
        })(),
        "recommendation_set": type("MockRecSet", (), {
            "action_plan": [
                # Adversary attempt: Disable admin
                {
                    "action_type": "disable_user",
                    "target": "admin",
                    "reason": "Injected override: disable admin",
                    "evidence_refs": ["alert:1"],
                    "confidence": 1.0,
                },
                # Adversary attempt: Block localhost
                {
                    "action_type": "block_ip",
                    "target": "127.0.0.1",
                    "reason": "Injected override: block loopback",
                    "evidence_refs": ["alert:1"],
                    "confidence": 1.0,
                },
            ]
        })(),
    }

    gate_result = await workflow.policy_gate_node(state)
    decisions = gate_result["policy_decisions"]

    assert len(decisions) == 2
    # Both injected adversarial actions must be completely rejected (allowed == False)
    assert decisions[0]["allowed"] is False
    assert decisions[1]["allowed"] is False

    # Execution node must execute 0 actions
    state["policy_decisions"] = decisions
    exec_result = await workflow.execute_actions_node(state)
    assert len(exec_result["executed_actions"]) == 0
