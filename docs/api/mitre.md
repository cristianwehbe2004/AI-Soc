# MITRE ATT&CK API

Sprint 6 exposes a pinned core Enterprise ATT&CK catalog and detection-rule mappings.

## Endpoints

```text
GET /api/v1/mitre/techniques
GET /api/v1/mitre/techniques/{external_id}
GET /api/v1/mitre/rules/{rule_id}/techniques
```

The technique list supports `tactic`, `search`, `limit`, and `offset` query parameters. Incident detail responses at `GET /api/v1/incidents/{incident_id}` include a deduplicated `techniques` array aggregated from the incident's attached alert rules.

## Seeded Mappings

| Detection rule | ATT&CK technique |
| --- | --- |
| `rule_001_brute_force` | `T1110` Brute Force |
| `rule_002_password_spray` | `T1110.003` Password Spraying |
| `rule_003_suspicious_privilege_change` | `T1098` Account Manipulation |
| `rule_004_large_download` | `T1005` Data from Local System |
| `rule_005_login_after_failures` | `T1078` Valid Accounts |

`rule_006_ml_anomaly` remains intentionally unmapped because a generic anomaly does not identify a specific ATT&CK behavior.
