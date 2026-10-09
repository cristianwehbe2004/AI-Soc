"use client";

import { useState, type FormEvent } from "react";
import { Network } from "lucide-react";
import { useAuth } from "@/components/providers/auth-provider";
import { useCreateIncidentEvidence, useIncidentEvidence } from "@/lib/api/hooks";
import type { IncidentEvidencePayload, NetworkObservation } from "@/lib/api/resources";
import { hasPermission } from "@/lib/auth/permissions";

const zones: NetworkObservation["source_zone"][] = ["internet", "dmz", "internal", "restricted", "unknown"];

export function IncidentEvidencePanel({ incidentId }: { incidentId: string }) {
  const { user } = useAuth();
  const evidence = useIncidentEvidence(incidentId);
  const create = useCreateIncidentEvidence(incidentId);
  const [kind, setKind] = useState<IncidentEvidencePayload["kind"]>("analyst_observation");
  const [source, setSource] = useState("");
  const [summary, setSummary] = useState("");
  const [sourceZone, setSourceZone] = useState<NetworkObservation["source_zone"]>("unknown");
  const [destinationZone, setDestinationZone] = useState<NetworkObservation["destination_zone"]>("unknown");
  const [port, setPort] = useState("");
  const [protocol, setProtocol] = useState<NetworkObservation["protocol"]>("tcp");
  const [disposition, setDisposition] = useState<NetworkObservation["disposition"]>("unknown");
  const canWrite = Boolean(user && hasPermission(user.role_name, "incidents:write"));

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const payload: IncidentEvidencePayload = { kind, source: source.trim(), summary: summary.trim() };
    if (kind === "network_observation") {
      payload.network = { source_zone: sourceZone, destination_zone: destinationZone, destination_port: Number(port), protocol, disposition };
    }
    await create.mutateAsync(payload);
    setSummary("");
  }

  return <section className="panel incident-panel" id="evidence">
    <div className="panel-heading"><div><p className="eyebrow">Source-backed investigation</p><h2>Incident evidence</h2></div><Network size={19} /></div>
    <p>Attach observations from logs, configuration reviews, or analyst reports. Do not paste passwords, private keys, or tokens. The app redacts common secret patterns before saving.</p>
    {evidence.isError ? <p className="inline-error">Could not load incident evidence.</p> : null}
    {!evidence.data?.length ? <p className="panel-empty">No attached evidence yet. The AI should treat this incident as a report, not proof of network exposure.</p> : null}
    {evidence.data?.map((item) => <article className="investigation-item" key={item.id}>
      <div><strong>{item.kind.replaceAll("_", " ")}</strong><small>{item.source} · {item.observed_at ? new Date(item.observed_at).toLocaleString() : "Time not supplied"}</small><p>{item.summary}</p>{item.network ? <small>{item.network.source_zone} → {item.network.destination_zone} · {item.network.protocol.toUpperCase()}/{item.network.destination_port} · {item.network.disposition}</small> : null}<small>Reference: evidence:{item.id}{item.sensitive_redacted ? " · secret redacted" : ""}</small></div>
    </article>)}
    {canWrite ? <form className="response-action-form" onSubmit={(event) => { void submit(event).catch(() => undefined); }}>
      <label>Evidence type<select value={kind} onChange={(event) => setKind(event.target.value as IncidentEvidencePayload["kind"])}><option value="analyst_observation">Analyst observation</option><option value="network_observation">Network observation</option><option value="asset_configuration">Asset configuration</option><option value="identity_activity">Identity activity</option><option value="vulnerability_report">Vulnerability report</option></select></label>
      <label>Source or system<input value={source} onChange={(event) => setSource(event.target.value)} minLength={3} maxLength={160} placeholder="e.g. firewall log, CMDB, analyst report" required /></label>
      <label>What was observed<textarea value={summary} onChange={(event) => setSummary(event.target.value)} minLength={8} maxLength={2000} required /></label>
      {kind === "network_observation" ? <div className="network-evidence-grid">
        <label>Source zone<select value={sourceZone} onChange={(event) => setSourceZone(event.target.value as NetworkObservation["source_zone"])}>{zones.map((zone) => <option key={zone}>{zone}</option>)}</select></label>
        <label>Destination zone<select value={destinationZone} onChange={(event) => setDestinationZone(event.target.value as NetworkObservation["destination_zone"])}>{zones.map((zone) => <option key={zone}>{zone}</option>)}</select></label>
        <label>Destination port<input type="number" min={1} max={65535} value={port} onChange={(event) => setPort(event.target.value)} required /></label>
        <label>Protocol<select value={protocol} onChange={(event) => setProtocol(event.target.value as NetworkObservation["protocol"])}><option value="tcp">TCP</option><option value="udp">UDP</option></select></label>
        <label>Disposition<select value={disposition} onChange={(event) => setDisposition(event.target.value as NetworkObservation["disposition"])}><option value="unknown">Unknown</option><option value="allowed">Allowed</option><option value="blocked">Blocked</option></select></label>
      </div> : null}
      {create.isError ? <p className="inline-error">{create.error instanceof Error ? create.error.message : "Evidence could not be saved."}</p> : null}
      <button type="submit" className="secondary-button" disabled={create.isPending}>Attach evidence</button>
    </form> : null}
  </section>;
}
