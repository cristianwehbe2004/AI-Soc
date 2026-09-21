from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from urllib import request


def normal_login(now: datetime) -> list[dict]:
    return [
        {
            "timestamp": (now - timedelta(minutes=2)).isoformat(),
            "source": "synthetic-auth",
            "source_type": "application",
            "event_type": "login_success",
            "category": "authentication",
            "severity": "low",
            "username": "alice",
            "source_ip": "192.168.10.10",
            "status": "success",
            "device_id": "device-alice-1",
            "raw_payload": {"scenario": "normal-login"},
            "metadata": {"synthetic": True, "scenario": "normal-login"},
        },
        {
            "timestamp": (now - timedelta(minutes=1)).isoformat(),
            "source": "synthetic-api",
            "source_type": "application",
            "event_type": "api_request",
            "category": "api",
            "severity": "low",
            "username": "alice",
            "source_ip": "192.168.10.10",
            "resource": "/documents/quarterly-report",
            "status": "success",
            "raw_payload": {"scenario": "normal-login"},
            "metadata": {"synthetic": True, "scenario": "normal-login"},
        },
    ]


def failed_login_burst(now: datetime, count: int) -> list[dict]:
    events = []
    for index in range(count):
        events.append(
            {
                "timestamp": (now - timedelta(seconds=count - index)).isoformat(),
                "source": "synthetic-auth",
                "source_type": "application",
                "event_type": "login_failure",
                "category": "authentication",
                "severity": "medium",
                "username": f"user{index % 5}",
                "source_ip": "203.0.113.50",
                "status": "failed",
                "raw_payload": {"scenario": "failed-login-burst", "sequence": index},
                "metadata": {"synthetic": True, "scenario": "failed-login-burst"},
            }
        )
    return events


def privilege_change_sequence(now: datetime) -> list[dict]:
    return [
        {
            "timestamp": (now - timedelta(minutes=10)).isoformat(),
            "source": "synthetic-auth",
            "source_type": "application",
            "event_type": "login_failure",
            "category": "authentication",
            "severity": "medium",
            "username": "admin-user",
            "source_ip": "198.51.100.77",
            "status": "failed",
            "raw_payload": {"scenario": "privilege-change-sequence", "sequence": 1},
            "metadata": {"synthetic": True, "scenario": "privilege-change-sequence"},
        },
        {
            "timestamp": (now - timedelta(minutes=3)).isoformat(),
            "source": "synthetic-auth",
            "source_type": "application",
            "event_type": "login_failure",
            "category": "authentication",
            "severity": "medium",
            "username": "admin-user",
            "source_ip": "198.51.100.77",
            "status": "failed",
            "raw_payload": {"scenario": "privilege-change-sequence", "sequence": 2},
            "metadata": {"synthetic": True, "scenario": "privilege-change-sequence"},
        },
        {
            "timestamp": now.isoformat(),
            "source": "synthetic-iam",
            "source_type": "cloud",
            "event_type": "privilege_change",
            "category": "privilege_change",
            "severity": "high",
            "username": "admin-user",
            "source_ip": "198.51.100.77",
            "status": "success",
            "action": "role_escalation",
            "raw_payload": {"scenario": "privilege-change-sequence", "sequence": 3},
            "metadata": {"synthetic": True, "scenario": "privilege-change-sequence"},
        },
    ]


def large_download(now: datetime) -> list[dict]:
    return [
        {
            "timestamp": now.isoformat(),
            "source": "synthetic-storage",
            "source_type": "application",
            "event_type": "file_download",
            "category": "file_access",
            "severity": "medium",
            "username": "bob",
            "source_ip": "203.0.113.120",
            "status": "success",
            "resource": "/exports/customer-data.csv",
            "bytes_received": 2500000,
            "raw_payload": {"scenario": "large-download"},
            "metadata": {"synthetic": True, "scenario": "large-download"},
        }
    ]


def login_after_failures(now: datetime) -> list[dict]:
    return [
        {
            "timestamp": (now - timedelta(minutes=9)).isoformat(),
            "source": "synthetic-auth",
            "source_type": "application",
            "event_type": "login_failure",
            "category": "authentication",
            "severity": "medium",
            "username": "charlie",
            "source_ip": "192.0.2.33",
            "status": "failed",
            "raw_payload": {"scenario": "login-after-failures", "sequence": 1},
            "metadata": {"synthetic": True, "scenario": "login-after-failures"},
        },
        {
            "timestamp": (now - timedelta(minutes=6)).isoformat(),
            "source": "synthetic-auth",
            "source_type": "application",
            "event_type": "login_failure",
            "category": "authentication",
            "severity": "medium",
            "username": "charlie",
            "source_ip": "192.0.2.33",
            "status": "failed",
            "raw_payload": {"scenario": "login-after-failures", "sequence": 2},
            "metadata": {"synthetic": True, "scenario": "login-after-failures"},
        },
        {
            "timestamp": (now - timedelta(minutes=1)).isoformat(),
            "source": "synthetic-auth",
            "source_type": "application",
            "event_type": "login_failure",
            "category": "authentication",
            "severity": "medium",
            "username": "charlie",
            "source_ip": "192.0.2.33",
            "status": "failed",
            "raw_payload": {"scenario": "login-after-failures", "sequence": 3},
            "metadata": {"synthetic": True, "scenario": "login-after-failures"},
        },
        {
            "timestamp": now.isoformat(),
            "source": "synthetic-auth",
            "source_type": "application",
            "event_type": "login_success",
            "category": "authentication",
            "severity": "low",
            "username": "charlie",
            "source_ip": "192.0.2.33",
            "status": "success",
            "raw_payload": {"scenario": "login-after-failures", "sequence": 4},
            "metadata": {"synthetic": True, "scenario": "login-after-failures"},
        },
    ]


def suspicious_api_behavior(now: datetime) -> list[dict]:
    return [
        {
            "timestamp": now.isoformat(),
            "source": "synthetic-api",
            "source_type": "application",
            "event_type": "api_error",
            "category": "api",
            "severity": "medium",
            "username": "service-account-7",
            "source_ip": "198.51.100.24",
            "status": "denied",
            "resource": "/admin/export",
            "raw_payload": {"scenario": "suspicious-api-behavior"},
            "metadata": {"synthetic": True, "scenario": "suspicious-api-behavior"},
        }
    ]


def credential_compromise(now: datetime) -> list[dict]:
    events = failed_login_burst(now - timedelta(minutes=10), 10)
    for item in events:
        item["raw_payload"]["scenario"] = "credential-compromise"
        item["metadata"]["scenario"] = "credential-compromise"

    events.extend(
        [
            {
                "timestamp": (now - timedelta(minutes=2)).isoformat(),
                "source": "synthetic-auth",
                "source_type": "application",
                "event_type": "login_failure",
                "category": "authentication",
                "severity": "medium",
                "username": "victim-admin",
                "source_ip": "203.0.113.50",
                "status": "failed",
                "raw_payload": {"scenario": "credential-compromise", "sequence": 11},
                "metadata": {"synthetic": True, "scenario": "credential-compromise"},
            },
            {
                "timestamp": (now - timedelta(minutes=1)).isoformat(),
                "source": "synthetic-auth",
                "source_type": "application",
                "event_type": "login_success",
                "category": "authentication",
                "severity": "low",
                "username": "victim-admin",
                "source_ip": "203.0.113.50",
                "status": "success",
                "raw_payload": {"scenario": "credential-compromise", "sequence": 12},
                "metadata": {"synthetic": True, "scenario": "credential-compromise"},
            },
            {
                "timestamp": now.isoformat(),
                "source": "synthetic-iam",
                "source_type": "cloud",
                "event_type": "privilege_change",
                "category": "privilege_change",
                "severity": "high",
                "username": "victim-admin",
                "source_ip": "203.0.113.50",
                "status": "success",
                "action": "role_escalation",
                "raw_payload": {"scenario": "credential-compromise", "sequence": 13},
                "metadata": {"synthetic": True, "scenario": "credential-compromise"},
            },
        ]
    )
    return events


def normal_telemetry(now: datetime, count: int) -> list[dict]:
    events = []
    users = ["alice", "bob", "charlie", "dana"]
    for index in range(count):
        username = users[index % len(users)]
        event_type = "login_success" if index % 4 == 0 else "api_request"
        category = "authentication" if event_type == "login_success" else "api"
        events.append(
            {
                "timestamp": (now - timedelta(seconds=(count - index) * 20)).isoformat(),
                "source": "synthetic-office",
                "source_type": "application",
                "event_type": event_type,
                "category": category,
                "severity": "low",
                "username": username,
                "source_ip": f"192.168.20.{10 + index % len(users)}",
                "status": "success",
                "resource": "/documents/handbook" if event_type == "api_request" else None,
                "bytes_sent": 500 + index % 200,
                "bytes_received": 2_000 + index % 1_000,
                "raw_payload": {"scenario": "normal-telemetry", "sequence": index},
                "metadata": {"synthetic": True, "scenario": "normal-telemetry"},
            }
        )
    return events


def abnormal_telemetry(now: datetime, count: int) -> list[dict]:
    events = []
    for index in range(count):
        event_type = "api_error"
        category = "api"
        if index % 10 == 8:
            event_type, category = "privilege_change", "privilege_change"
        elif index % 10 == 9:
            event_type, category = "resource_access", "file_access"
        events.append(
            {
                "timestamp": (now - timedelta(seconds=count - index)).isoformat(),
                "source": "synthetic-compromised-host",
                "source_type": "application",
                "event_type": event_type,
                "category": category,
                "severity": "high",
                "username": f"target-{index % 15}",
                "source_ip": "198.51.100.200",
                "status": "denied" if event_type == "api_error" else "success",
                "resource": "/admin/export",
                "bytes_sent": 100_000,
                "bytes_received": 5_000_000 + index * 100_000,
                "raw_payload": {"scenario": "abnormal-telemetry", "sequence": index},
                "metadata": {"synthetic": True, "scenario": "abnormal-telemetry"},
            }
        )
    return events


def send_events(base_url: str, events: list[dict], api_key: str) -> dict:
    payload = json.dumps({"events": events}).encode("utf-8")
    req = request.Request(
        url=f"{base_url.rstrip('/')}/api/v1/events/bulk",
        data=payload,
        headers={"Content-Type": "application/json", "X-API-Key": api_key},
        method="POST",
    )
    with request.urlopen(req) as response:
        return json.loads(response.read().decode("utf-8"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate synthetic SOC events.")
    parser.add_argument(
        "scenario",
        choices=[
            "normal-login",
            "failed-login-burst",
            "privilege-change-sequence",
            "large-download",
            "login-after-failures",
            "suspicious-api-behavior",
            "credential-compromise",
            "normal-telemetry",
            "abnormal-telemetry",
        ],
    )
    parser.add_argument("--count", type=int, default=20, help="Number of events for burst scenarios.")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API base URL for ingestion.")
    parser.add_argument("--send", action="store_true", help="POST generated events to the backend API.")
    parser.add_argument(
        "--api-key",
        default=os.getenv("AI_SOC_API_KEY"),
        help="Ingestion key; defaults to AI_SOC_API_KEY.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    now = datetime.now(timezone.utc)

    if args.scenario == "normal-login":
        events = normal_login(now)
    elif args.scenario == "failed-login-burst":
        events = failed_login_burst(now, args.count)
    elif args.scenario == "privilege-change-sequence":
        events = privilege_change_sequence(now)
    elif args.scenario == "large-download":
        events = large_download(now)
    elif args.scenario == "login-after-failures":
        events = login_after_failures(now)
    elif args.scenario == "credential-compromise":
        events = credential_compromise(now)
    elif args.scenario == "normal-telemetry":
        events = normal_telemetry(now, args.count)
    elif args.scenario == "abnormal-telemetry":
        events = abnormal_telemetry(now, args.count)
    else:
        events = suspicious_api_behavior(now)

    if args.send:
        if not args.api_key:
            raise SystemExit("--api-key or AI_SOC_API_KEY is required with --send")
        result = send_events(args.base_url, events, args.api_key)
        print(json.dumps(result, indent=2))
        return

    print(json.dumps(events, indent=2))


if __name__ == "__main__":
    main()
