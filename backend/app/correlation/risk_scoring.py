from __future__ import annotations

from app.models.alert import Alert


class RiskScoringEngine:
    def __init__(self, settings) -> None:
        self.settings = settings

    def score(self, alerts: list[Alert]) -> int:
        if not alerts:
            return 0

        severity_score = 0
        confidences = []
        rule_ids = {alert.rule_id for alert in alerts}
        for alert in alerts:
            severity_score += self._severity_weight(alert.severity)
            confidences.append(float(alert.confidence))

        confidence_score = int((sum(confidences) / len(confidences)) * self.settings.risk_score_confidence_multiplier)

        combo_bonus = 0
        if "rule_005_login_after_failures" in rule_ids and (
            "rule_001_brute_force" in rule_ids or "rule_002_password_spray" in rule_ids
        ):
            combo_bonus += self.settings.risk_score_combo_bonus
        if "rule_003_suspicious_privilege_change" in rule_ids or "rule_004_large_download" in rule_ids:
            combo_bonus += self.settings.risk_score_supporting_bonus

        raw_score = severity_score + confidence_score + combo_bonus
        return max(0, min(100, raw_score))

    @staticmethod
    def severity_from_score(score: int) -> str:
        if score >= 85:
            return "critical"
        if score >= 65:
            return "high"
        if score >= 35:
            return "medium"
        return "low"

    def _severity_weight(self, severity: str) -> int:
        if severity == "critical":
            return self.settings.risk_score_high_severity_weight + 10
        if severity == "high":
            return self.settings.risk_score_high_severity_weight
        if severity == "medium":
            return self.settings.risk_score_medium_severity_weight
        return self.settings.risk_score_low_severity_weight
