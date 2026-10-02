import { describe, expect, it } from "vitest";
import { realtimeUrl } from "./client";

describe("realtime client", () => {
  it("uses the WebSocket protocol and one-time ticket", () => {
    const url = new URL(realtimeUrl("ticket-value"));

    expect(url.protocol).toBe("ws:");
    expect(url.pathname).toBe("/api/v1/realtime");
    expect(url.searchParams.get("ticket")).toBe("ticket-value");
  });
});