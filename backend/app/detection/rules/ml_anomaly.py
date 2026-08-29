from __future__ import annotations

from app.detection.base import DetectionContext, DetectionResult
from app.models.event import Event


class MLAnomalyRule:
    id = "rule_006_ml_anomaly"
    name = "ML telemetry anomaly"
    severity = "medium"

    async def evaluate(self, event: Event, context: DetectionContext) -> DetectionResult | None:
        if context.ml_inference_service is None:
            return None
        anomaly = await context.ml_inference_service.score_event(event, context.event_repository)
        if anomaly is None or not anomaly.is_anomaly:
            return None
        distance = anomaly.threshold - anomaly.score
        confidence = min(0.90, max(0.60, 0.60 + distance))
        return DetectionResult(
            rule_id=self.id,
            title="Anomalous telemetry detected",
            description=(
                f"{event.event_type} anomaly score {anomaly.score:.4f} crossed "
                f"the {anomaly.threshold:.4f} threshold"
            ),
            severity=self.severity,
            confidence=round(confidence, 2),
            source_ip=event.source_ip,
            username=event.username,
            event_id=event.event_id,
            evidence={
                "anomaly_score": anomaly.score,
                "threshold": anomaly.threshold,
                "feature_version": anomaly.feature_version,
                "model_version": anomaly.model_version,
                "features": anomaly.features,
            },
            first_seen=event.timestamp,
            last_seen=event.timestamp,
        )
