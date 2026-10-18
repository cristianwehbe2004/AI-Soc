import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { IncidentResponsePanel } from "./incident-response-panel";

const { mutateAsync } = vi.hoisted(() => ({ mutateAsync: vi.fn().mockResolvedValue({}) }));

vi.mock("@/components/providers/auth-provider", () => ({
  useAuth: () => ({ user: { id: "analyst-1", role_name: "analyst" } }),
}));
vi.mock("@/lib/api/hooks", () => ({
  useResponseActions: () => ({ data: [] }),
  useIncidentEvidence: () => ({ data: [{ id: "evidence-1", kind: "network_observation", source: "firewall export" }] }),
  useProposeResponseAction: () => ({ mutateAsync, isPending: false }),
  useDecideResponseAction: () => ({ mutate: vi.fn() }),
}));

describe("response evidence selection", () => {
  it("requires selection and submits only the sources selected by the analyst", async () => {
    render(<IncidentResponsePanel incidentId="incident-1" alertIds={["alert-1"]} />);
    const submit = screen.getByRole("button", { name: "Propose for approval" });
    expect(submit).toBeDisabled();
    fireEvent.click(screen.getByLabelText("network observation · firewall export"));
    expect(submit).toBeEnabled();
    fireEvent.change(screen.getByLabelText("App user UUID"), {
      target: { value: "00000000-0000-0000-0000-000000000001" },
    });
    fireEvent.change(screen.getByLabelText("Evidence-based rationale"), {
      target: { value: "Revoke sessions while the reported access is investigated" },
    });
    fireEvent.submit(submit.closest("form")!);
    await waitFor(() => expect(mutateAsync).toHaveBeenCalledWith(expect.objectContaining({
      evidence_refs: ["evidence:evidence-1"],
    })));
    expect(screen.getByLabelText("Incident report")).not.toBeChecked();
  });
});
