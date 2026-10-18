"""Conservative, evidence-linked network observations; no active scanning."""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas.investigation import EvidenceFinding, Recommendation, RemediationPlan

SENSITIVE_PORTS = {22, 445, 1433, 3306, 3389, 5432, 5900, 6379, 9200, 27017}


@dataclass(frozen=True)
class NetworkAssessment:
    findings: list[EvidenceFinding]
    recommendations: list[Recommendation]
    gaps: list[str]


def assess_network_evidence(items: list[dict]) -> NetworkAssessment:
    findings = []
    recommendations = []
    relevant = [item for item in items if item.get("kind") == "network_observation" and isinstance(item.get("network"), dict)]
    for item in relevant:
        network = item["network"]
        if network.get("disposition") != "allowed":
            continue
        source = network.get("source_zone")
        destination = network.get("destination_zone")
        port = network.get("destination_port")
        if not isinstance(port, int):
            continue
        internet_to_private = source == "internet" and destination in {"internal", "restricted"}
        lateral_to_restricted = source in {"dmz", "internal"} and destination == "restricted" and port in SENSITIVE_PORTS
        if not (internet_to_private or lateral_to_restricted):
            continue
        sensitive = port in SENSITIVE_PORTS
        title = "Reported internet access to a sensitive service" if internet_to_private and sensitive else (
            "Reported internet path into a private zone" if internet_to_private else "Possible segmentation gap into a restricted zone"
        )
        reference = item["ref"]
        findings.append(EvidenceFinding(
            title=title,
            summary=(f"Analyst-supplied {item.get('source', 'network')} evidence reports an allowed "
                     f"{network.get('protocol', 'tcp').upper()}/{port} path from {source} to {destination}. "
                     "This is a reported exposure, not an independently verified vulnerability."),
            severity="high" if internet_to_private and sensitive else "medium",
            confidence=0.6 if internet_to_private and sensitive else 0.5,
            evidence_refs=[reference],
        ))
        recommendations.append(Recommendation(
            title=f"Review and restrict reported {network.get('protocol', 'tcp').upper()}/{port} access",
            priority="high" if internet_to_private and sensitive else "medium",
            rationale="The supplied network observation suggests a path that may exceed intended access policy; verify before changing production rules.",
            actions=[
                "Verify the observation against firewall, flow, and asset-owner records.",
                "If unauthorized, limit the rule to approved sources and required destinations under change control.",
                "Test legitimate traffic after the change and monitor for repeat attempts.",
            ],
            evidence_refs=[reference],
            remediation_plan=RemediationPlan(
                verification_steps=[
                    "Confirm the affected assets and the reported path using firewall rules, flow logs, and the asset owner's intended access policy.",
                ],
                change_steps=[
                    "Save the current rule configuration and obtain the approved change window.",
                    "Restrict the unauthorized path to the approved sources, destinations, and ports; retain a tested administrator access path.",
                ],
                validation_steps=[
                    "Verify that an unauthorized source is blocked and required business traffic still succeeds.",
                    "Review firewall and flow logs for continued access attempts after the change.",
                ],
                rollback_steps=[
                    "If required traffic fails, restore the approved previous configuration or a narrower temporary rule while investigating the failure.",
                    "Verify administrator access and document any remaining exposure with the incident owner.",
                ],
                impact="Restricting this path can interrupt legitimate remote administration or application connections; confirm dependencies with the asset owner.",
            ),
        ))
    gaps = []
    if not relevant:
        gaps.append("No structured network observation was supplied; network exposure and segmentation cannot be assessed.")
    elif not findings:
        gaps.append("No risky allowed path was identified in supplied observations; this does not prove the network is secure.")
    return NetworkAssessment(findings[:10], recommendations[:10], gaps)
