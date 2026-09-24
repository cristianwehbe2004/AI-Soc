import { describe, expect, it } from "vitest";
import { adminNavigationForRole } from "./navigation";

describe("role-aware navigation", () => {
  it("hides administration from viewers and analysts", () => {
    expect(adminNavigationForRole("viewer")).toEqual([]);
    expect(adminNavigationForRole("analyst")).toEqual([]);
  });

  it("shows every administration destination to administrators", () => {
    expect(adminNavigationForRole("admin").map((item) => item.label)).toEqual([
      "Users",
      "API keys",
      "Audit log",
    ]);
  });
});
