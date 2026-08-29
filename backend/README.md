# AI-SOC Backend

The backend currently supports event ingestion, rule-based alerting, incident correlation, and Sprint 5 ML anomaly detection.

- FastAPI application
- environment-driven settings
- PostgreSQL and Redis connectivity
- Alembic migrations
- JSON logging
- health endpoint
- pytest coverage

## ML Workflow

Generate at least 200 normal telemetry events before training, then run:

```bash
python scripts/generate_ml_dataset.py --output artifacts/datasets/events_v1.csv
python scripts/train_isolation_forest.py artifacts/datasets/events_v1.csv
python scripts/evaluate_isolation_forest.py
```

The trained artifact is stored under `ML_ARTIFACT_DIR`, and its metadata and active status are stored in `model_registry`. Once a model is active, event ingestion scores each event inline and persists `rule_006_ml_anomaly` alerts when the configured threshold is crossed.

From the repository root, the same workflow is available as `make ml-dataset`, `make ml-train`, and `make ml-evaluate`.
