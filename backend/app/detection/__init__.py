"""Detection package."""

from app.core.config import get_settings
from app.detection.engine import DetectionEngine
from app.detection.registry import RuleRegistry
from app.detection.rules import (
    BruteForceRule,
    LargeDownloadRule,
    LoginAfterFailuresRule,
    PasswordSprayRule,
    SuspiciousPrivilegeChangeRule,
)


def build_detection_engine() -> DetectionEngine:
    settings = get_settings()
    registry = RuleRegistry(
        [
            BruteForceRule(),
            PasswordSprayRule(),
            SuspiciousPrivilegeChangeRule(),
            LargeDownloadRule(),
            LoginAfterFailuresRule(),
        ]
    )
    return DetectionEngine(registry)
