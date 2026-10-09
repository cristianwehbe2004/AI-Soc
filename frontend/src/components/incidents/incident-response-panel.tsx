"use client";

import { useState } from "react";
import { ShieldCheck } from "lucide-react";
import { useAuth } from "@/components/providers/auth-provider";
import { useDecideResponseAction, useIncidentEvidence, useProposeResponseAction, useResponseActions } from "@/lib/api/hooks";
import type { ResponseActionType } from "@/lib/api/resources";
import { hasPermission } from "@/lib/auth/permissions";

const ACTIONS: { value: ResponseActionType; label: string; impact: string }[] = [
  { value: "revoke_app_sessions", label: "Revoke app sessions", impact: "Signs the selected app user out of all active sessions." },
  { value: "disable_aws_access_key", label: "Disable AWS access key", impact: "Disables the selected IAM access key; workloads using it may stop." },
  { value: "block_s3_public_access", label: "Block S3 public access", impact: "Applies all four bucket-level public-access blocks; a public website or integration may stop working." },
];

export function IncidentResponsePanel({ incidentId, alertIds }: { incidentId: string; alertIds: string[] }) {
  const { user } = useAuth();
  const actions = useResponseActions(incidentId);
  const evidence = useIncidentEvidence(incidentId);
  const propose = useProposeResponseAction(incidentId);
  const decide = useDecideResponseAction(incidentId);
  const [type, setType] = useState<ResponseActionType>("revoke_app_sessions");
  const [target, setTarget] = useState("");
  const [accountId, setAccountId] = useState("");
  const [rationale, setRationale] = useState("");
  const [impact, setImpact] = useState(ACTIONS[0].impact);
  const canPropose = Boolean(user && hasPermission(user.role_name, "responses:propose"));
  const canApprove = Boolean(user && hasPermission(user.role_name, "responses:approve"));

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const linkedRefs = [...alertIds.map((id) => `alert:${id}`), ...(evidence.data ?? []).map((item) => `evidence:${item.id}`)].slice(0, 20);
    await propose.mutateAsync({
      action_type: type,
      target: target.trim(),
      account_id: type === "revoke_app_sessions" ? null : accountId.trim(),
      rationale: rationale.trim(),
      impact: impact.trim(),
      evidence_refs: linkedRefs.length ? linkedRefs : [`incident:${incidentId}`],
      idempotency_key: crypto.randomUUID(),
    });
    setTarget("");
    setRationale("");
  }

  return <section className="panel incident-panel">
    <div className="panel-heading"><div><p className="eyebrow">Controlled defense</p><h2>Response actions</h2></div><ShieldCheck size={19} /></div>
    <p>Actions require a separate administrator approval. AWS execution is disabled unless explicitly configured on the server.</p>
    {actions.isError ? <p className="inline-error">Could not load response actions.</p> : null}
    {actions.data?.map((action) => <article className="investigation-item" key={action.id}>
      <div><span className={`status-badge status-${action.status}`}>{action.status}</span><strong>{ACTIONS.find((option) => option.value === action.action_type)?.label}</strong><small>{action.target}{action.account_id ? ` · AWS ${action.account_id}` : ""}</small><small>Impact: {action.impact}</small><small>Evidence: {action.evidence_refs.join(", ")}</small>{action.error ? <small className="inline-error">{action.error}</small> : null}</div>
      {action.status === "proposed" && canApprove && user?.id !== action.proposed_by ? <div className="filter-actions"><button type="button" className="secondary-button" disabled={decide.isPending} onClick={() => decide.mutate({ actionId: action.id, decision: "approve" })}>Approve</button><button type="button" className="secondary-button" disabled={decide.isPending} onClick={() => decide.mutate({ actionId: action.id, decision: "reject" })}>Reject</button></div> : null}
    </article>)}
    {decide.isError ? <p className="inline-error">{decide.error instanceof Error ? decide.error.message : "Decision failed."}</p> : null}
    {canPropose ? <form className="response-action-form" onSubmit={(event) => { void submit(event).catch(() => undefined); }}>
      <label>Action<select value={type} onChange={(event) => { const next = event.target.value as ResponseActionType; setType(next); setImpact(ACTIONS.find((option) => option.value === next)?.impact ?? ""); }}>{ACTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
      <label>{type === "revoke_app_sessions" ? "App user UUID" : type === "disable_aws_access_key" ? "IAM username:access-key-ID" : "S3 bucket name"}<input value={target} onChange={(event) => setTarget(event.target.value)} required /></label>
      {type !== "revoke_app_sessions" ? <label>AWS account ID<input value={accountId} onChange={(event) => setAccountId(event.target.value)} pattern="[0-9]{12}" required /></label> : null}
      <label>Evidence-based rationale<textarea value={rationale} onChange={(event) => setRationale(event.target.value)} minLength={10} required /></label>
      <label>Expected impact<textarea value={impact} onChange={(event) => setImpact(event.target.value)} minLength={10} required /></label>
      <small>Evidence: {alertIds.length} alerts, {evidence.data?.length ?? 0} attached observations. Only sources shown here are linked.</small>
      {propose.isError ? <p className="inline-error">{propose.error instanceof Error ? propose.error.message : "Proposal failed."}</p> : null}
      <button className="secondary-button" disabled={propose.isPending} type="submit">Propose for approval</button>
    </form> : null}
  </section>;
}
