import {
  apiRequest,
  getAccessToken,
  loginSession,
  resetApiClientForTests,
} from "./client";
import { afterEach, describe, expect, it, vi } from "vitest";

const user = {
  id: "b5374a57-c2aa-4e90-908b-548b84465968",
  email: "analyst@example.com",
  full_name: "SOC Analyst",
  role_name: "analyst" as const,
  is_active: true,
  last_login_at: null,
  created_at: "2026-09-21T12:00:00Z",
  updated_at: "2026-09-21T12:00:00Z",
};

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", "X-Request-ID": "request-1" },
  });
}

describe("API client", () => {
  afterEach(() => {
    resetApiClientForTests();
    vi.unstubAllGlobals();
  });

  it("keeps the access token in memory and attaches it to protected calls", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ access_token: "memory-token", token_type: "bearer", expires_in: 900, user }))
      .mockResolvedValueOnce(jsonResponse({ items: [] }));
    vi.stubGlobal("fetch", fetchMock);
    const storageSpy = vi.spyOn(Storage.prototype, "setItem");

    await loginSession("analyst@example.com", "correct-password");
    await apiRequest("/events");

    expect(getAccessToken()).toBe("memory-token");
    expect(storageSpy).not.toHaveBeenCalled();
    const headers = fetchMock.mock.calls[1][1]?.headers as Headers;
    expect(headers.get("Authorization")).toBe("Bearer memory-token");
  });

  it("coordinates one refresh and retries concurrent unauthorized requests", async () => {
    let protectedCalls = 0;
    let refreshCalls = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: string | URL | Request) => {
        const url = String(input);
        if (url.endsWith("/auth/refresh")) {
          refreshCalls += 1;
          return jsonResponse({ access_token: "renewed-token", token_type: "bearer", expires_in: 900, user });
        }
        protectedCalls += 1;
        if (protectedCalls <= 2) return jsonResponse({ detail: "Not authenticated" }, 401);
        return jsonResponse({ ok: true });
      }),
    );

    const [first, second] = await Promise.all([
      apiRequest<{ ok: boolean }>("/incidents"),
      apiRequest<{ ok: boolean }>("/events"),
    ]);

    expect(first.ok).toBe(true);
    expect(second.ok).toBe(true);
    expect(refreshCalls).toBe(1);
  });
});
