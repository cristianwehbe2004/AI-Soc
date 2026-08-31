"""Detection package."""

from app.detection.engine import DetectionEngine
from app.detection.registry import RuleRegistry
from app.detection.rules import (
    BruteForceRule,
    LargeDownloadRule,
    LoginAfterFailuresRule,
    MLAnomalyRule,
    PasswordSprayRule,
    SuspiciousPrivilegeChangeRule,
)


def build_rule_registry() -> RuleRegistry:
    return RuleRegistry(
        [
            BruteForceRule(),
            PasswordSprayRule(),
            SuspiciousPrivilegeChangeRule(),
            LargeDownloadRule(),
            LoginAfterFailuresRule(),
            MLAnomalyRule(),
        ]
    )


def build_detection_engine() -> DetectionEngine:
    return DetectionEngine(build_rule_registry())
