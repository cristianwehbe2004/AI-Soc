# AI-SOC Backend

The backend currently supports event ingestion, rule-based and ML alerting, incident correlation, and MITRE ATT&CK aggregation.

- FastAPI application
- environment-driven settings
- PostgreSQL and Redis connectivity
- Alembic migrations
- JSON logging
- health endpoint
- pytest coverage
- pinned ATT&CK technique catalog and rule mappings

## MITRE ATT&CK

Read the seeded catalog at `GET /api/v1/mitre/techniques`, inspect one technique by external ID, or query mappings at `GET /api/v1/mitre/rules/{rule_id}/techniques`. Incident detail responses include techniques aggregated from attached alert rules.

## ML Workflow

Generate at least 200 normal telemetry events before training, then run:

```bash
python scripts/generate_ml_dataset.py --output artifacts/datasets/events_v1.csv
python scripts/train_isolation_forest.py artifacts/datasets/events_v1.csv
python scripts/evaluate_isolation_forest.py
```

The trained artifact is stored under `ML_ARTIFACT_DIR`, and its metadata and active status are stored in `model_registry`. Once a model is active, event ingestion scores each event inline and persists `rule_006_ml_anomaly` alerts when the configured threshold is crossed.

From the repository root, the same workflow is available as `make ml-dataset`, `make ml-train`, and `make ml-evaluate`.
