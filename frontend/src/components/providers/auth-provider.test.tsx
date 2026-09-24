import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { resetApiClientForTests } from "@/lib/api/client";
import { AuthProvider, resetAuthBootstrapForTests, useAuth } from "./auth-provider";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn(), refresh: vi.fn() }),
}));

const user = {
  id: "b5374a57-c2aa-4e90-908b-548b84465968",
  email: "viewer@example.com",
  full_name: "SOC Viewer",
  role_name: "viewer",
  is_active: true,
  last_login_at: null,
  created_at: "2026-09-21T12:00:00Z",
  updated_at: "2026-09-21T12:00:00Z",
};

function Probe() {
  const { status, user: currentUser } = useAuth();
  return <div>{status}:{currentUser?.email ?? "none"}</div>;
}

describe("AuthProvider", () => {
  afterEach(() => {
    resetApiClientForTests();
    resetAuthBootstrapForTests();
    vi.unstubAllGlobals();
  });

  it("restores a browser session using the refresh cookie contract", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ access_token: "restored", token_type: "bearer", expires_in: 900, user }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    render(<AuthProvider><Probe /></AuthProvider>);

    await waitFor(() => expect(screen.getByText("authenticated:viewer@example.com")).toBeInTheDocument());
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/auth/refresh"),
      expect.objectContaining({ credentials: "include" }),
    );
  });

  it("becomes anonymous when no refresh session exists", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "Invalid refresh token" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      }),
    ));

    render(<AuthProvider><Probe /></AuthProvider>);
    await waitFor(() => expect(screen.getByText("anonymous:none")).toBeInTheDocument());
  });
});
