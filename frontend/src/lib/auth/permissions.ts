import type { RoleName } from "@/lib/api/types";

export type Permission =
  | "soc:read"
  | "investigations:create"
  | "users:manage"
  | "api_keys:manage"
  | "audit:read";

const ROLE_PERMISSIONS: Record<RoleName, ReadonlySet<Permission>> = {
  viewer: new Set(["soc:read"]),
  analyst: new Set(["soc:read", "investigations:create"]),
  admin: new Set([
    "soc:read",
    "investigations:create",
    "users:manage",
    "api_keys:manage",
    "audit:read",
  ]),
};

export function hasPermission(role: RoleName, permission: Permission) {
  return ROLE_PERMISSIONS[role].has(permission);
}

export function canAccessAdmin(role: RoleName) {
  return hasPermission(role, "users:manage");
}
