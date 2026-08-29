from __future__ import annotations

from app.detection.base import DetectionRule


class RuleRegistry:
    def __init__(self, rules: list[DetectionRule]) -> None:
        self._rules = list(rules)
        self._rules_by_id: dict[str, DetectionRule] = {}
        for rule in self._rules:
            if rule.id in self._rules_by_id:
                raise ValueError(f"Duplicate detection rule id: {rule.id}")
            self._rules_by_id[rule.id] = rule

    def all(self) -> list[DetectionRule]:
        return list(self._rules)

    def get(self, rule_id: str) -> DetectionRule | None:
        return self._rules_by_id.get(rule_id)
