# Response actions API

All endpoints require an authenticated session except AWS finding ingestion, which requires an `events:write` service API key. The frontend uses the same endpoints and receives `response.*` WebSocket notifications after state changes; REST remains authoritative.

- `POST /api/v1/aws/findings/bulk`: `{"findings": [<ASFF finding>, ...]}`; maximum 100. Existing Security Hub-format findings are normalized and deduplicated by account, finding ID, and update time. Archived, resolved, and suppressed findings are skipped. This does not activate Security Hub or make AWS API calls.
- `GET /api/v1/incidents/{id}/response-actions`: list response proposals and outcomes (SOC reader).
- `POST /api/v1/incidents/{id}/response-actions`: propose (analyst/admin). Body: `action_type`, `target`, `account_id` (AWS only), `rationale`, `impact`, `evidence_refs`, `idempotency_key`. References must belong to the incident: `incident:<uuid>`, `alert:<uuid>`, or `event:<event_id>`.
- `POST /api/v1/response-actions/{id}/approve` or `/reject`: admin only; proposer cannot decide their own proposal. Approval queues worker execution. A database recovery scan picks up approved actions after a Redis interruption.
- `GET /api/v1/response-actions/{id}`: status and verified result.

`revoke_app_sessions` targets a user UUID. `disable_aws_access_key` targets `IAM-username:AKIA...` and needs an AWS account ID. `block_s3_public_access` targets a bucket name and needs an AWS account ID. AWS response is off by default and needs dedicated least-privilege credentials, `AWS_RESPONSE_ENABLED=true`, and explicit account/bucket allowlists. Test in a non-production account first. A failed action is recorded; operators must inspect AWS state before proposing a retry because an external mutation may have succeeded even if verification failed.
