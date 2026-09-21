from enum import StrEnum


class Permission(StrEnum):
    SOC_READ = "soc:read"
    INVESTIGATIONS_CREATE = "investigations:create"
    USERS_MANAGE = "users:manage"
    API_KEYS_MANAGE = "api_keys:manage"
    AUDIT_READ = "audit:read"


ROLE_PERMISSIONS: dict[str, frozenset[Permission]] = {
    "viewer": frozenset({Permission.SOC_READ}),
    "analyst": frozenset({Permission.SOC_READ, Permission.INVESTIGATIONS_CREATE}),
    "admin": frozenset(Permission),
}


def permissions_for_role(role: str) -> frozenset[Permission]:
    return ROLE_PERMISSIONS.get(role, frozenset())
