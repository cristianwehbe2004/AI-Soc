import { ApiError } from "@/lib/api/client";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import LoginPage from "./page";

const login = vi.fn();
const replace = vi.fn();

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace }) }));
vi.mock("@/components/providers/auth-provider", () => ({
  useAuth: () => ({ status: "anonymous", login }),
}));

describe("login page", () => {
  beforeEach(() => {
    login.mockReset();
    replace.mockReset();
  });

  it("submits credentials without persisting them", async () => {
    const user = userEvent.setup();
    login.mockResolvedValue(undefined);
    const storageSpy = vi.spyOn(Storage.prototype, "setItem");
    render(<LoginPage />);

    await user.type(screen.getByLabelText("Email address"), "analyst@example.com");
    await user.type(screen.getByLabelText("Password", { exact: true }), "correct-password");
    fireEvent.submit(screen.getByRole("button", { name: "Enter operations" }).closest("form")!);

    await waitFor(() => expect(login).toHaveBeenCalledWith("analyst@example.com", "correct-password"));
    expect(storageSpy).not.toHaveBeenCalled();
  });

  it("explains backend throttling without exposing account state", async () => {
    login.mockRejectedValue(new ApiError(429, "Too many authentication attempts", "request-1", {}));
    render(<LoginPage />);
    fireEvent.change(screen.getByLabelText("Email address"), { target: { value: "viewer@example.com" } });
    fireEvent.change(screen.getByLabelText("Password", { exact: true }), { target: { value: "incorrect-password" } });
    fireEvent.submit(screen.getByRole("button", { name: "Enter operations" }).closest("form")!);

    expect(await screen.findByRole("alert")).toHaveTextContent("Wait 15 minutes");
  });
});
