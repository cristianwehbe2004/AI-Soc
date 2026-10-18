import type { components } from "@/lib/api/schema";

type Plan = components["schemas"]["RemediationPlan"];

const phases = [
  ["verification_steps", "Verify the weakness"],
  ["change_steps", "Apply the fix"],
  ["validation_steps", "Check the outcome"],
  ["rollback_steps", "Rollback if needed"],
] as const;

export function RemediationPlanView({ plan }: { plan: Plan }) {
  return (
    <section className="remediation-plan" aria-label="Remediation plan">
      <p><strong>Expected impact:</strong> {plan.impact}</p>
      {phases.map(([key, title]) => (
        <section key={key}>
          <h4>{title}</h4>
          <ol>{plan[key].map((step, index) => <li key={`${key}-${index}`}>{step}</li>)}</ol>
        </section>
      ))}
    </section>
  );
}
