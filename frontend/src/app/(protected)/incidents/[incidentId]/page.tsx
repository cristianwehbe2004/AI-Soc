"use client";

import Link from "next/link";
import { ArrowLeft, Clock3, Fingerprint, ShieldAlert } from "lucide-react";
import { useParams } from "next/navigation";
import { useIncident } from "@/lib/api/hooks";
import { ErrorState, LoadingState } from "@/components/ui/data-state";
import { PageHeading } from "@/components/ui/page-heading";
import { IncidentAlertsPanel } from "@/components/incidents/incident-alerts-panel";
import { IncidentInvestigationsPanel } from "@/components/incidents/incident-investigations-panel";
import { IncidentMLPanel } from "@/components/incidents/incident-ml-panel";
import { IncidentMitrePanel } from "@/components/incidents/incident-mitre-panel";
import { IncidentTimeline } from "@/components/incidents/incident-timeline";
import { AnalystNotesPanel } from "@/components/incidents/analyst-notes-panel";
import { IncidentResponsePanel } from "@/components/incidents/incident-response-panel";

function queryError(error: unknown) {
  return error instanceof Error ? error : new Error("The API returned an unknown error.");
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en-US", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export default function IncidentDetailPage() {
  const params = useParams<{ incidentId: string }>();
  const incident = useIncident(params.incidentId);

  if (incident.isLoading) return <LoadingState label="Loading incident workspace" />;
  if (incident.isError || !incident.data) return <ErrorState error={queryError(incident.error)} onRetry={() => void incident.refetch()} />;

  const item = incident.data;
  return (
    <div className="page-stack">
      <Link className="back-link" href="/incidents"><ArrowLeft size={15} /> Back to incidents</Link>
      <PageHeading eyebrow="Incident workspace" title={item.title} description={item.description} action={<span className={`severity-badge severity-${item.severity}`}>{item.severity} / {item.risk_score}</span>} />
      <section className="incident-summary panel"><div><span>Status</span><strong className={`status-badge status-${item.status}`}>{item.status}</strong></div><div><span>Identity</span><strong>{item.primary_username ?? "Unattributed"}</strong></div><div><span>Source IP</span><strong>{item.primary_source_ip ?? "—"}</strong></div><div><span>First seen</span><strong>{formatDate(item.first_seen)}</strong></div><div><span>Last seen</span><strong>{formatDate(item.last_seen)}</strong></div></section>
      <div className="incident-workspace">
        <main className="incident-main"><IncidentTimeline entries={item.timeline} /><IncidentAlertsPanel alerts={item.alerts} /><IncidentMitrePanel techniques={item.techniques} /></main>
        <aside className="incident-rail"><IncidentMLPanel incidentId={item.id} /><IncidentInvestigationsPanel incidentId={item.id} /><IncidentResponsePanel incidentId={item.id} alertIds={item.alerts.map((alert) => alert.id)} /><AnalystNotesPanel incidentId={item.id} initialNotes={item.notes} /></aside>
      </div>
      <div className="incident-footnote"><Clock3 size={14} /> <span>Evidence timeline is materialized by correlation.</span><Fingerprint size={14} /> <span>{item.techniques.length} MITRE techniques mapped.</span><ShieldAlert size={14} /> <span>{item.alerts.length} alerts correlated.</span></div>
    </div>
  );
}
