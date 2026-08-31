from __future__ import annotations


def build_correlation_key(
    username: str | None,
    source_ip: str | None,
) -> str:
    normalized_username = (username or "").strip().lower()
    normalized_source_ip = (source_ip or "").strip().lower()
    return (
        f"credential_compromise:u:{len(normalized_username)}:"
        f"{normalized_username}|s:{len(normalized_source_ip)}:"
        f"{normalized_source_ip}"
    )


def build_identity_lock_keys(
    username: str | None,
    source_ip: str | None,
) -> list[str]:
    keys = []
    normalized_username = (username or "").strip().lower()
    normalized_source_ip = (source_ip or "").strip().lower()
    if normalized_username:
        keys.append(
            f"credential_compromise:username:{len(normalized_username)}:"
            f"{normalized_username}"
        )
    if normalized_source_ip:
        keys.append(
            f"credential_compromise:source_ip:{len(normalized_source_ip)}:"
            f"{normalized_source_ip}"
        )
    return sorted(keys)
