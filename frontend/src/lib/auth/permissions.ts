import type { RoleName } from "@/lib/api/types";

export type Permission =
  | "soc:read"
  | "incidents:write"
  | "investigations:create"
  | "users:manage"
  | "api_keys:manage"
  | "audit:read"
  | "responses:propose"
  | "responses:approve";

const ROLE_PERMISSIONS: Record<RoleName, ReadonlySet<Permission>> = {
  viewer: new Set(["soc:read"]),
  analyst: new Set(["soc:read", "incidents:write", "investigations:create", "responses:propose"]),
  admin: new Set([
    "soc:read",
    "incidents:write",
    "investigations:create",
    "users:manage",
    "api_keys:manage",
    "audit:read",
    "responses:propose",
    "responses:approve",
  ]),
};

export function hasPermission(role: RoleName, permission: Permission) {
  return ROLE_PERMISSIONS[role].has(permission);
}

export function canAccessAdmin(role: RoleName) {
  return hasPermission(role, "users:manage");
}
