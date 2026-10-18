# pyrefly: ignore[missing-import]
import pytest
from app.response.actions import ActionPlan, ActionTier, ActionType, ProposedAction
from app.response.audit_chain import canonical_json, compute_entry_hash, verify_chain
from app.response.circuit_breaker import CircuitBreaker
from app.response.policy import PolicyContext, PolicyDecision, PolicyEngine


@pytest.mark.asyncio
async def test_action_models_validation():
    # Valid action
    action = ProposedAction(
        action_type=ActionType.BLOCK_IP,
        target="198.51.100.22",
        reason="Repeated brute force password attacks",
        evidence_refs=["alert:alert-123"],
        confidence=0.95,
        ttl_seconds=3600,
    )
    assert action.tier == ActionTier.TIER_1_LOW
    assert action.ttl_seconds == 3600

    # Extra fields forbidden
    with pytest.raises(Exception):
        ProposedAction(
            action_type=ActionType.BLOCK_IP,
            target="198.51.100.22",
            reason="Repeated brute force",
            evidence_refs=["alert:1"],
            confidence=0.9,
            arbitrary_injection="malicious_payload",
        )


@pytest.mark.asyncio
async def test_policy_target_grounding():
    engine = PolicyEngine()
    context = PolicyContext(
        incident_id="inc-1",
        incident_entities={"victim_user", "198.51.100.50"},
        valid_evidence_refs={"alert:1", "event:100"},
    )

    # Valid grounded action
    valid_action = ProposedAction(
        action_type=ActionType.BLOCK_IP,
        target="198.51.100.50",
        reason="Attacker IP",
        evidence_refs=["alert:1"],
        confidence=0.95,
    )
    decision = await engine.evaluate(valid_action, context)
    assert decision.allowed is True
    assert decision.requires_human_approval is False

    # Ungrounded target (e.g. LLM hallucinates or attacker injects an unverified IP)
    hallucinated_action = ProposedAction(
        action_type=ActionType.BLOCK_IP,
        target="203.0.113.99",
        reason="Attacker IP",
        evidence_refs=["alert:1"],
        confidence=0.95,
    )
    decision = await engine.evaluate(hallucinated_action, context)
    assert decision.allowed is False
    assert "not present in incident entities" in decision.reason


@pytest.mark.asyncio
async def test_policy_protected_entities_and_subnets():
    engine = PolicyEngine()
    context = PolicyContext(
        incident_id="inc-1",
        incident_entities={"admin", "127.0.0.1", "169.254.169.254", "attacker_user"},
        valid_evidence_refs={"alert:1"},
    )

    # Attempt to disable admin account (even if present in incident entities)
    admin_action = ProposedAction(
        action_type=ActionType.DISABLE_USER,
        target="admin",
        reason="Suspicious login on admin",
        evidence_refs=["alert:1"],
        confidence=0.99,
    )
    decision = await engine.evaluate(admin_action, context)
    assert decision.allowed is False
    assert "protected entity" in decision.reason

    # Attempt to block localhost / 127.0.0.1
    loopback_action = ProposedAction(
        action_type=ActionType.BLOCK_IP,
        target="127.0.0.1",
        reason="Localhost attack",
        evidence_refs=["alert:1"],
        confidence=0.99,
    )
    decision = await engine.evaluate(loopback_action, context)
    assert decision.allowed is False
    assert "protected" in decision.reason


@pytest.mark.asyncio
async def test_policy_risk_tier_routing():
    engine = PolicyEngine()
    context = PolicyContext(
        incident_id="inc-1",
        incident_entities={"compromised_user", "attacker_ip"},
        valid_evidence_refs={"alert:1"},
        min_auto_confidence=0.85,
    )

    # Tier 2 (Disable User) requires human approval even with 1.0 confidence
    user_disable = ProposedAction(
        action_type=ActionType.DISABLE_USER,
        target="compromised_user",
        reason="Compromised user",
        evidence_refs=["alert:1"],
        confidence=1.0,
    )
    decision = await engine.evaluate(user_disable, context)
    assert decision.allowed is True
    assert decision.requires_human_approval is True
    assert "Tier 2" in decision.reason

    # Tier 1 with lower confidence requires human approval
    low_conf_ip = ProposedAction(
        action_type=ActionType.BLOCK_IP,
        target="attacker_ip",
        reason="Possible attacker",
        evidence_refs=["alert:1"],
        confidence=0.70,
    )
    decision = await engine.evaluate(low_conf_ip, context)
    assert decision.allowed is True
    assert decision.requires_human_approval is True
    assert "below auto-execution threshold" in decision.reason


@pytest.mark.asyncio
async def test_circuit_breaker_and_kill_switch():
    cb = CircuitBreaker(max_actions_per_hour=2, max_disruptive_actions_per_hour=1)
    engine = PolicyEngine(circuit_breaker=cb)
    context = PolicyContext(
        incident_id="inc-1",
        incident_entities={"victim_ip"},
        valid_evidence_refs={"alert:1"},
    )

    action = ProposedAction(
        action_type=ActionType.BLOCK_IP,
        target="victim_ip",
        reason="Attacker IP",
        evidence_refs=["alert:1"],
        confidence=0.95,
    )

    # 1. First execution OK
    dec = await engine.evaluate(action, context)
    assert dec.allowed is True
    await cb.record_execution(is_disruptive=False)

    # 2. Second execution OK
    dec = await engine.evaluate(action, context)
    assert dec.allowed is True
    await cb.record_execution(is_disruptive=False)

    # 3. Third execution hits max_actions_per_hour cap
    dec = await engine.evaluate(action, context)
    assert dec.allowed is False
    assert "Hourly total action cap reached" in dec.reason

    # 4. Test global kill switch
    cb_fresh = CircuitBreaker()
    engine_fresh = PolicyEngine(circuit_breaker=cb_fresh)
    await cb_fresh.set_kill_switch(True)
    dec = await engine_fresh.evaluate(action, context)
    assert dec.allowed is False
    assert "Global response kill switch is ACTIVE" in dec.reason


def test_audit_hash_chain():
    initial_hash = "0" * 64

    entry_1 = {"id": "1", "action": "block_ip", "target": "1.2.3.4"}
    prev_1 = initial_hash
    hash_1 = compute_entry_hash(prev_1, {"action": "block_ip", "target": "1.2.3.4", "prev_hash": prev_1})
    record_1 = {**entry_1, "prev_hash": prev_1, "record_hash": hash_1}

    entry_2 = {"id": "2", "action": "revoke_sessions", "target": "user@example.com"}
    prev_2 = hash_1
    hash_2 = compute_entry_hash(prev_2, {"action": "revoke_sessions", "target": "user@example.com", "prev_hash": prev_2})
    record_2 = {**entry_2, "prev_hash": prev_2, "record_hash": hash_2}

    # Valid chain passes
    valid, err = verify_chain([record_1, record_2])
    assert valid is True
    assert err is None

    # Tampered payload fails
    tampered_record = dict(record_1)
    tampered_record["target"] = "8.8.8.8"  # Maliciously altered IP
    valid, err = verify_chain([tampered_record, record_2])
    assert valid is False
    assert "tampered" in err.lower()

    # Broken link fails
    broken_link_record = dict(record_2)
    broken_link_record["prev_hash"] = "broken" * 8
    valid, err = verify_chain([record_1, broken_link_record])
    assert valid is False
    assert "Broken chain linkage" in err
