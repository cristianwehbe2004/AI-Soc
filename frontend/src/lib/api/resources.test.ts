import { afterEach, describe, expect, it, vi } from "vitest";
import { getDashboardSummary, listEvents, updateIncidentNote } from "./resources";
import { resetApiClientForTests } from "./client";

function jsonResponse(body: unknown) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

describe("API resources", () => {
  afterEach(() => {
    resetApiClientForTests();
    vi.unstubAllGlobals();
  });

  it("serializes event filters and dashboard requests", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ items: [], total: 0, limit: 25, offset: 0 }));
    vi.stubGlobal("fetch", fetchMock);

    await listEvents({ severity: "high", limit: 25, offset: 50 });
    await getDashboardSummary();

    expect(String(fetchMock.mock.calls[0][0])).toContain("/events?severity=high&limit=25&offset=50");
    expect(String(fetchMock.mock.calls[1][0])).toContain("/dashboard/summary");
  });

  it("uses PATCH for note updates", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({}));
    vi.stubGlobal("fetch", fetchMock);

    await updateIncidentNote("incident-1", "note-1", "Updated evidence");

    expect(fetchMock.mock.calls[0][1]).toMatchObject({
      method: "PATCH",
      body: JSON.stringify({ content: "Updated evidence" }),
    });
  });
});