from __future__ import annotations

from typing import Any

from fastapi import Request

SENSITIVE_KEYS = {
    "authorization",
    "cookie",
    "password",
    "password_hash",
    "refresh_token",
    "access_token",
    "api_key",
    "secret",
    "raw_payload",
}


def sanitize_audit_details(value: Any, *, depth: int = 0) -> Any:
    if depth > 4:
        return "[truncated]"
    if isinstance(value, dict):
        return {
            str(key)[:128]: sanitize_audit_details(item, depth=depth + 1)
            for key, item in list(value.items())[:50]
            if str(key).casefold() not in SENSITIVE_KEYS
        }
    if isinstance(value, list):
        return [sanitize_audit_details(item, depth=depth + 1) for item in value[:50]]
    if isinstance(value, str):
        return value[:512]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return str(value)[:512]


def request_metadata(request: Request) -> dict[str, str | None]:
    return {
        "request_id": getattr(request.state, "request_id", None),
        "method": request.method,
        "path": request.url.path,
        "source_ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent", "")[:512] or None,
    }
