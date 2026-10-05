# Incident-type training and response rollout

The existing Isolation Forest remains the event anomaly detector. The new multi-label incident classifier predicts `credential_compromise`, `privilege_abuse`, `data_exfiltration`, `cloud_exposure`, and `exposed_credentials` from normalized event counts, distinct identities/IPs, severity, and transfer sizes. It never executes a response. AI investigations may see its output as contextual evidence, not ground truth.

## Training data

### Public example research corpus

`backend/data/public_incident_examples.jsonl` contains 113 source-linked scenarios collected from a pinned revision of [OTRF Security Datasets](https://github.com/OTRF/Security-Datasets). Reproduce with `python scripts/collect_public_incident_examples.py` from `backend/`. The collector reads only small metadata YAML files, waits between requests, and stores titles, bounded summaries, tags, platforms, ATT&CK IDs, SHA-256 provenance, and links. It never downloads raw archives, simulation instructions, or adversary transcripts. All records say `review_status=unreviewed` and `train_ready=false`.

This corpus is **not** the classifier's training dataset. The scenarios are simulations rather than independent confirmed production incidents; 109 mention Windows, only two mention AWS, and just one mentions exfiltration in the projected metadata. They provide no normalized per-incident event windows or verified benign controls. Furthermore, the upstream [LICENSE file](https://github.com/OTRF/Security-Datasets/blob/master/LICENSE) says MIT while its [README](https://github.com/OTRF/Security-Datasets) says GPL-3.0; resolve the inconsistency before redistribution or model training from source content. Do not invent events or labels from scenario titles to meet the 100-row training threshold. [LANL's public red-team dataset](https://lanl.ma.ic.ac.uk/data/cyber1/) is another possible credential-compromise source, but its matching authentication logs are multi-gigabyte and would need a bounded, provenance-preserving extraction before use. No AWS service or free credits were consumed to collect this corpus.

The next dataset step is to assemble incident-level windows from this app's authorized telemetry and/or licensed public raw logs, with analyst-verified labels and benign cases, then run the training command below. Keep source provenance and group related windows from the same scenario/account so they cannot leak between train, validation, and test slices.

### Training-only database

`training_incidents` is physically separate from the operational `incidents`, `events`, and `alerts` tables. Its rows do not appear in the SOC UI, trigger detections, queue AI investigations, or execute response actions. The idempotent `python scripts/seed_training_incidents.py` command inserts 113 unreviewed OTRF metadata references (no labels or event windows) and 180 deterministic synthetic lab cases (30 benign plus 30 per incident label). Their `source_kind` and `review_status` are explicit, and the public references have no asserted observation time.

Use `python scripts/train_incident_classifier.py --from-db --lab-shadow` only to test the pipeline. It creates a **shadow** model; its metrics describe recognition of six generated templates and must not be treated as real-world detection performance. `--activate` rejects synthetic, unreviewed, unknown-source, or empty-event cases even if the numeric evaluation gates pass. Normal `--from-db` training selects only approved `reviewed_internal` or `reviewed_public_telemetry` cases, so the current seed does not provide an activatable dataset.

Use reviewed, authorized incidents as JSONL. Each line needs a unique `incident_id`, an `account_id` for grouping/audit, UTC `observed_at`, zero or more `labels`, and normalized `events` with `event_type`, `severity`, `username`, `source_ip`, and optional numeric `bytes_sent`/`bytes_received`. Include benign incidents, confirmed positives, and hard negatives (for example, intentionally public S3 websites and approved admin changes). Remove secrets and personal data before export. Do not train on investigation text or unreviewed model outputs. At least 100 distinct incidents are required; each label needs positive and negative examples in the chronological training slice.

Run locally in the backend container or Python environment:

```bash
python scripts/train_incident_classifier.py artifacts/datasets/reviewed_incidents.jsonl
```

This creates a **shadow** model only. The split is chronological 60% train / 20% threshold selection / 20% held-out test, with no incident duplicated across slices. Inspect the registry's per-label precision, recall, false-positive rate, support, and chosen threshold. Only after human review, run with `--activate`; activation requires every label to reach precision and recall >= 0.80, false-positive rate <= 0.05, and >= 3 positive held-out cases. This is a minimum gate, not proof of production fitness. Check calibration, drift, class imbalance, and performance by account before promotion. Roll back by reactivating the previous registry version. The `/api/v1/incidents/{id}/classification` endpoint returns active-model labels and probabilities, or `unavailable`.

## Incident coverage and defenses

Ingest app authentication/permission events and normalized AWS Security Finding Format findings using `/api/v1/aws/findings/bulk`. A cloud finding yields an alert and account/finding-keyed incident. Security Hub is **not enabled or polled by this app**; an operator may submit an existing export or existing upstream feed. Treat external finding text as untrusted. Responses are a separate workflow: analyst proposes an evidence-linked action with impact statement; a different administrator approves or rejects; a worker rechecks scope, executes, verifies, and audits. Supported actions: revoke this app's sessions, deactivate an allowlisted-account IAM access key, and enable four S3 bucket Block Public Access settings for an allowlisted prefix. No LLM can call these actions.

## AWS free-credit guardrails

The classifier trains on the existing local backend CPU and filesystem—no SageMaker, GPU instance, or AWS storage is provisioned. `AWS_RESPONSE_ENABLED=false` is the default, and AWS execution also requires `AWS_ALLOWED_ACCOUNT_IDS`; S3 additionally requires `AWS_ALLOWED_BUCKET_PREFIX`. The ingest endpoint is push-only, capped at 100 findings per request, deduplicated, and stores only selected fields. Avoid enabling Security Hub, GuardDuty, CloudTrail Lake, or data-event trails solely for this feature without checking current charges. CloudTrail Event History can be used manually for management-event context without adding a trail, but it does not provide all data-access events. Set AWS Budgets alerts and review Cost Explorer before any AWS expansion.

## Security fundamentals and references

- Evidence integrity and provenance: immutable event IDs, deduplication, bounded normalized payloads, incident-linked evidence references, and audit records. Follow [NIST SP 800-61 Rev. 3](https://csrc.nist.gov/pubs/sp/800/61/r3/final) for response preparation, analysis, containment, and recovery.
- Least privilege and separation of duties: proposal and approval are distinct RBAC capabilities; self-approval is rejected; AWS account and bucket scopes are allowlisted. See [AWS IAM access-key guidance](https://docs.aws.amazon.com/IAM/latest/UserGuide/id-credentials-access-keys-update.html).
- Defense in depth and safe containment: verify AWS account identity and resource ownership before mutation; verify the post-action state. An S3 block may interrupt legitimate public workloads, so the impact is reviewed first. See [S3 Block Public Access](https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-block-public-access.html).
- Minimize sensitive data and resist prompt injection: send bounded context to the AI investigator, never secrets, and keep LLM output out of the execution path. See [OWASP LLM Top 10](https://genai.owasp.org/llm-top-10/).
- Cost-aware collection: [CloudTrail Event History pricing](https://aws.amazon.com/cloudtrail/pricing/) and the [Security Hub cost estimator](https://docs.aws.amazon.com/securityhub/latest/userguide/security-hub-cost-estimator.html). [ASFF required fields](https://docs.aws.amazon.com/securityhub/latest/userguide/asff-required-attributes.html) define the finding import shape.
