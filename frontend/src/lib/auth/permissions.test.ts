import { canAccessAdmin, hasPermission } from "./permissions";
import { describe, expect, it } from "vitest";

describe("role permissions", () => {
  it("keeps viewers read-only", () => {
    expect(hasPermission("viewer", "soc:read")).toBe(true);
    expect(hasPermission("viewer", "investigations:create")).toBe(false);
    expect(canAccessAdmin("viewer")).toBe(false);
  });

  it("allows analysts to request investigations but not administer users", () => {
    expect(hasPermission("analyst", "investigations:create")).toBe(true);
    expect(hasPermission("analyst", "users:manage")).toBe(false);
  });

  it("allows administrators to use every frontend capability", () => {
    expect(hasPermission("admin", "soc:read")).toBe(true);
    expect(hasPermission("admin", "investigations:create")).toBe(true);
    expect(hasPermission("admin", "users:manage")).toBe(true);
    expect(hasPermission("admin", "api_keys:manage")).toBe(true);
    expect(hasPermission("admin", "audit:read")).toBe(true);
  });
});
