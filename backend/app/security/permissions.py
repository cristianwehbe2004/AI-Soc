from enum import StrEnum


class Permission(StrEnum):
    SOC_READ = "soc:read"
    INCIDENTS_WRITE = "incidents:write"
    INVESTIGATIONS_CREATE = "investigations:create"
    RESPONSES_PROPOSE = "responses:propose"
    RESPONSES_APPROVE = "responses:approve"
    USERS_MANAGE = "users:manage"
    API_KEYS_MANAGE = "api_keys:manage"
    AUDIT_READ = "audit:read"


ROLE_PERMISSIONS: dict[str, frozenset[Permission]] = {
    "viewer": frozenset({Permission.SOC_READ}),
    "analyst": frozenset({Permission.SOC_READ, Permission.INCIDENTS_WRITE, Permission.INVESTIGATIONS_CREATE, Permission.RESPONSES_PROPOSE}),
    "admin": frozenset(Permission),
}


def permissions_for_role(role: str) -> frozenset[Permission]:
    return ROLE_PERMISSIONS.get(role, frozenset())
