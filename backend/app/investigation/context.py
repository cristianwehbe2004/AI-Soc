from __future__ import annotations

import json
import re
import uuid
from typing import Any

from app.repositories.event_repository import EventRepository
from app.repositories.incident_repository import IncidentRepository
from app.repositories.mitre_repository import MitreRepository
from app.schemas.investigation import InvestigationContext

CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class IncidentNotFoundError(LookupError):
    pass


class InvestigationContextTooLargeError(ValueError):
    pass


class InvestigationContextBuilder:
    def __init__(
        self,
        *,
        incident_repository: IncidentRepository,
        event_repository: EventRepository,
        mitre_repository: MitreRepository,
        max_chars: int,
    ) -> None:
        self.incident_repository = incident_repository
        self.event_repository = event_repository
        self.mitre_repository = mitre_repository
        self.max_chars = max_chars

    async def build(self, incident_id: uuid.UUID) -> InvestigationContext:
        incident = await self.incident_repository.get(incident_id)
        if incident is None:
            raise IncidentNotFoundError(str(incident_id))

        alerts = await self.incident_repository.get_alerts_for_incident(incident_id)
        events_by_id = await self.event_repository.get_by_ids(
            [alert.event_id for alert in alerts]
        )
        techniques = await self.mitre_repository.get_for_rules(
            [alert.rule_id for alert in alerts]
        )

        alert_context = [self._alert_context(alert) for alert in alerts]
        event_context = [
            self._event_context(events_by_id[alert.event_id])
            for alert in alerts
            if alert.event_id in events_by_id
        ]
        technique_context = [
            {
                "technique_id": technique.external_id,
                "name": technique.name,
                "tactics": technique.tactics,
                "description": self._clean_string(technique.description, 1000),
            }
            for technique in techniques
        ]
        valid_refs = [f"alert:{alert.id}" for alert in alerts]
        valid_refs.extend(
            f"event:{event['event_id']}" for event in event_context
        )
        valid_refs.extend(
            f"mitre:{technique['technique_id']}" for technique in technique_context
        )
        context = InvestigationContext(
            incident={
                "id": str(incident.id),
                "title": self._clean_string(incident.title, 255),
                "description": self._clean_string(incident.description, 2000),
                "status": incident.status,
                "severity": incident.severity,
                "risk_score": incident.risk_score,
                "primary_username": self._clean_optional(incident.primary_username),
                "primary_source_ip": self._clean_optional(incident.primary_source_ip),
                "first_seen": incident.first_seen.isoformat(),
                "last_seen": incident.last_seen.isoformat(),
            },
            alerts=alert_context,
            events=event_context,
            timeline=self._sanitize(incident.timeline, depth=0),
            techniques=technique_context,
            valid_evidence_refs=sorted(set(valid_refs)),
        )
        return self._enforce_size(context)

    def _alert_context(self, alert) -> dict[str, Any]:
        return {
            "ref": f"alert:{alert.id}",
            "id": str(alert.id),
            "rule_id": alert.rule_id,
            "title": self._clean_string(alert.title, 255),
            "description": self._clean_string(alert.description, 1500),
            "severity": alert.severity,
            "confidence": float(alert.confidence),
            "source_ip": self._clean_optional(alert.source_ip),
            "username": self._clean_optional(alert.username),
            "first_seen": alert.first_seen.isoformat(),
            "last_seen": alert.last_seen.isoformat(),
            "evidence": self._sanitize(alert.evidence, depth=0),
        }

    def _event_context(self, event) -> dict[str, Any]:
        return {
            "ref": f"event:{event.event_id}",
            "event_id": event.event_id,
            "timestamp": event.timestamp.isoformat(),
            "source": self._clean_string(event.source, 255),
            "source_type": event.source_type,
            "event_type": event.event_type,
            "category": event.category,
            "severity": event.severity,
            "username": self._clean_optional(event.username),
            "source_ip": self._clean_optional(event.source_ip),
            "destination_ip": self._clean_optional(event.destination_ip),
            "hostname": self._clean_optional(event.hostname),
            "action": self._clean_optional(event.action),
            "status": self._clean_optional(event.status),
            "resource": self._clean_optional(event.resource),
            "bytes_sent": event.bytes_sent,
            "bytes_received": event.bytes_received,
        }

    def _sanitize(self, value: Any, *, depth: int) -> Any:
        if depth >= 4:
            return "[truncated]"
        if isinstance(value, dict):
            return {
                self._clean_string(str(key), 100): self._sanitize(item, depth=depth + 1)
                for key, item in list(value.items())[:50]
            }
        if isinstance(value, list):
            return [self._sanitize(item, depth=depth + 1) for item in value[:50]]
        if isinstance(value, str):
            return self._clean_string(value, 1000)
        if value is None or isinstance(value, (bool, int, float)):
            return value
        return self._clean_string(str(value), 1000)

    def _enforce_size(self, context: InvestigationContext) -> InvestigationContext:
        serialized = context.model_dump(mode="json")
        if self._serialized_size(serialized) <= self.max_chars:
            return context

        serialized["timeline"] = serialized["timeline"][-50:]
        serialized["alerts"] = serialized["alerts"][-50:]
        serialized["events"] = serialized["events"][-50:]
        serialized["incident"]["context_truncated"] = True
        for alert in serialized["alerts"]:
            alert["description"] = alert["description"][:500]
            alert["evidence"] = self._sanitize(alert["evidence"], depth=2)
        for entry in serialized["timeline"]:
            if isinstance(entry, dict):
                entry["description"] = str(entry.get("description", ""))[:500]
                entry["metadata"] = {}

        while self._serialized_size(serialized) > self.max_chars:
            if len(serialized["timeline"]) > 1:
                serialized["timeline"].pop(0)
            elif len(serialized["events"]) > 1:
                serialized["events"].pop(0)
            elif len(serialized["alerts"]) > 1:
                serialized["alerts"].pop(0)
            else:
                raise InvestigationContextTooLargeError(
                    "Safe incident context exceeds LLM_CONTEXT_MAX_CHARS"
                )

        serialized["valid_evidence_refs"] = sorted(
            {
                *[item["ref"] for item in serialized["alerts"]],
                *[item["ref"] for item in serialized["events"]],
                *[
                    f"mitre:{item['technique_id']}"
                    for item in serialized["techniques"]
                ],
            }
        )
        return InvestigationContext.model_validate(serialized)

    @staticmethod
    def _serialized_size(value: dict) -> int:
        return len(json.dumps(value, separators=(",", ":")))

    def _clean_optional(self, value: str | None) -> str | None:
        return None if value is None else self._clean_string(value, 500)

    @staticmethod
    def _clean_string(value: str, limit: int) -> str:
        return CONTROL_CHARACTERS.sub("", value).strip()[:limit]
