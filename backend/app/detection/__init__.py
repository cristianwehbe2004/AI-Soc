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
from app.detection.rules.cloud_finding import CloudFindingRule


def build_rule_registry() -> RuleRegistry:
    return RuleRegistry(
        [
            BruteForceRule(),
            PasswordSprayRule(),
            SuspiciousPrivilegeChangeRule(),
            LargeDownloadRule(),
            LoginAfterFailuresRule(),
            MLAnomalyRule(),
            CloudFindingRule(),
        ]
    )


def build_detection_engine() -> DetectionEngine:
    return DetectionEngine(build_rule_registry())
