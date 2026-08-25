from __future__ import annotations

from app.detection.base import DetectionRule


class RuleRegistry:
    def __init__(self, rules: list[DetectionRule]) -> None:
        self._rules = rules

    def all(self) -> list[DetectionRule]:
        return list(self._rules)
