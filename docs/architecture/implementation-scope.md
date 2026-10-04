# Current Implementation Scope

The current capability work is intentionally limited to AI investigation
operationalization. It adds policy-controlled automatic investigation dispatch,
severity gating, and per-incident cooldown deduplication after successful event
commits.

Google AI Studio remains the configured real LLM provider. Autonomous
containment, copilot/RAG, threat-intelligence enrichment, ML retraining,
response playbooks, and AWS/IaC deployment are separate phases and are not part
of this change.