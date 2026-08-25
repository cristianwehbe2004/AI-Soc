from __future__ import annotations

from datetime import timedelta

from app.correlation.risk_scoring import RiskScoringEngine
from app.correlation.timeline import build_incident_timeline
from app.models.alert import Alert
from app.models.incident import Incident
from app.repositories.alert_repository import AlertRepository
from app.repositories.event_repository import EventRepository
from app.repositories.incident_repository import IncidentRepository


class IncidentCorrelationService:
    def __init__(
        self,
        *,
        alert_repository: AlertRepository,
        event_repository: EventRepository,
        incident_repository: IncidentRepository,
        settings,
    ) -> None:
        self.alert_repository = alert_repository
        self.event_repository = event_repository
        self.incident_repository = incident_repository
        self.settings = settings
        self.risk_scoring = RiskScoringEngine(settings)

    async def correlate(self, alerts: list[Alert]) -> list[Incident]:
        incidents: list[Incident] = []
        for alert in alerts:
            incident = await self._correlate_alert(alert)
            if incident is not None and incident.id not in {item.id for item in incidents}:
                incidents.append(incident)
        return incidents

    async def _correlate_alert(self, alert: Alert) -> Incident | None:
        if alert.rule_id not in {
            "rule_001_brute_force",
            "rule_002_password_spray",
            "rule_003_suspicious_privilege_change",
            "rule_004_large_download",
            "rule_005_login_after_failures",
        }:
            return None

        lookback_since = alert.last_seen - timedelta(seconds=self.settings.credential_compromise_lookback_seconds)
        related = await self.alert_repository.related_alerts(
            username=alert.username,
            source_ip=alert.source_ip,
            since=lookback_since,
        )
        if alert.id not in {item.id for item in related}:
            related.append(alert)
        candidate_alerts = self._credential_compromise_candidates(related)
        if not candidate_alerts:
            return None

        username = self._select_primary_username(candidate_alerts)
        source_ip = self._select_primary_source_ip(candidate_alerts)
        merge_since = alert.last_seen - timedelta(seconds=self.settings.incident_merge_window_seconds)
        incident = await self.incident_repository.find_open_related_incident(
            username=username,
            source_ip=source_ip,
            since=merge_since,
        )

        event_ids = [item.event_id for item in candidate_alerts]
        events_by_id = await self.event_repository.get_by_ids(event_ids)
        timeline = build_incident_timeline(candidate_alerts, events_by_id)
        risk_score = self.risk_scoring.score(candidate_alerts)
        severity = self.risk_scoring.severity_from_score(risk_score)

        if incident is None:
            incident = Incident(
                title="Credential compromise incident",
                description="Correlated attack activity indicates a likely credential compromise sequence.",
                status="open",
                severity=severity,
                risk_score=risk_score,
                primary_username=username,
                primary_source_ip=source_ip,
                first_seen=min(item.first_seen for item in candidate_alerts),
                last_seen=max(item.last_seen for item in candidate_alerts),
                timeline=timeline,
            )
            incident = await self.incident_repository.create(incident)
        else:
            incident.severity = severity
            incident.risk_score = risk_score
            incident.primary_username = username or incident.primary_username
            incident.primary_source_ip = source_ip or incident.primary_source_ip
            incident.first_seen = min(incident.first_seen, min(item.first_seen for item in candidate_alerts))
            incident.last_seen = max(incident.last_seen, max(item.last_seen for item in candidate_alerts))
            incident.timeline = timeline
            incident.description = "Correlated attack activity indicates a likely credential compromise sequence."
            await self.incident_repository.update(incident)

        await self.incident_repository.add_alert_links(incident.id, [item.id for item in candidate_alerts])
        incident.timeline = timeline
        return incident

    def _credential_compromise_candidates(self, alerts: list[Alert]) -> list[Alert]:
        rule_ids = {alert.rule_id for alert in alerts}
        has_initial_access = "rule_001_brute_force" in rule_ids or "rule_002_password_spray" in rule_ids
        has_success = "rule_005_login_after_failures" in rule_ids
        if not (has_initial_access and has_success):
            return []

        allowed_rules = {
            "rule_001_brute_force",
            "rule_002_password_spray",
            "rule_003_suspicious_privilege_change",
            "rule_004_large_download",
            "rule_005_login_after_failures",
        }
        return [alert for alert in alerts if alert.rule_id in allowed_rules]

    @staticmethod
    def _first_present(values: list[str | None]) -> str | None:
        for value in values:
            if value:
                return value
        return None

    def _select_primary_username(self, alerts: list[Alert]) -> str | None:
        for preferred_rule in [
            "rule_005_login_after_failures",
            "rule_003_suspicious_privilege_change",
            "rule_004_large_download",
        ]:
            username = self._first_present([alert.username for alert in alerts if alert.rule_id == preferred_rule])
            if username is not None:
                return username
        return self._first_present([alert.username for alert in alerts])

    def _select_primary_source_ip(self, alerts: list[Alert]) -> str | None:
        for preferred_rule in [
            "rule_005_login_after_failures",
            "rule_003_suspicious_privilege_change",
            "rule_004_large_download",
            "rule_001_brute_force",
            "rule_002_password_spray",
        ]:
            source_ip = self._first_present([alert.source_ip for alert in alerts if alert.rule_id == preferred_rule])
            if source_ip is not None:
                return source_ip
        return self._first_present([alert.source_ip for alert in alerts])
