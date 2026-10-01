"use client";

import Link from "next/link";
import { Activity, BrainCircuit, Radar, ShieldCheck, TrendingUp } from "lucide-react";
import type { CSSProperties } from "react";
import { useDashboardSummary, useIncidents } from "@/lib/api/hooks";
import { ErrorState, EmptyState, LoadingState } from "@/components/ui/data-state";
import { PageHeading } from "@/components/ui/page-heading";

const metricDefinitions = [
  { label: "Events observed", key: "events_total", note: "All normalized telemetry", icon: Activity },
  { label: "Open incidents", key: "incidents_open", note: "Open or investigating", icon: Radar },
  { label: "Active alerts", key: "alerts_active", note: "Not resolved or dismissed", icon: ShieldCheck },
  { label: "AI investigations", key: "investigations_active", note: "Queued or running", icon: BrainCircuit },
] as const;

function formatNumber(value: number | undefined) {
  return value === undefined ? "—" : new Intl.NumberFormat("en-US").format(value);
}

function queryError(error: unknown) {
  return error instanceof Error ? error : new Error("The API returned an unknown error.");
}

export default function DashboardPage() {
  const summary = useDashboardSummary();
  const incidents = useIncidents({ limit: 5, offset: 0 });
  const summaryData = summary.data;

  return (
    <div className="page-stack dashboard-page">
      <PageHeading
        eyebrow="Operational overview"
        title="Security posture, without the noise."
        description="A focused command surface for detection, correlation, and evidence-led investigation."
        action={
          <span className={`status-pill ${summaryData?.model_status === "active" ? "live" : "neutral"}`}>
            <span /> {summaryData?.model_status === "active" ? "Monitoring enabled" : "Monitoring available"}
          </span>
        }
      />

      <section className="metric-grid" aria-label="SOC metrics">
        {metricDefinitions.map(({ label, key, note, icon: Icon }, index) => (
          <article className="metric-card panel" key={label} style={{ "--delay": `${index * 70}ms` } as CSSProperties}>
            <div className="metric-top"><span>{label}</span><Icon size={18} /></div>
            <strong>{formatNumber(summaryData?.[key])}</strong>
            <p>{note}</p>
          </article>
        ))}
      </section>

      {summary.isLoading ? <LoadingState label="Refreshing operational metrics" /> : null}
      {summary.isError ? <ErrorState error={queryError(summary.error)} onRetry={() => void summary.refetch()} /> : null}

      <section className="dashboard-grid">
        <article className="panel priority-panel">
          <div className="panel-heading">
            <div><p className="eyebrow">Priority queue</p><h2>Incident triage</h2></div>
            <Link className="text-link" href="/incidents">View all</Link>
          </div>
          {incidents.isLoading ? <LoadingState label="Loading incidents" /> : null}
          {incidents.isError ? <ErrorState error={queryError(incidents.error)} onRetry={() => void incidents.refetch()} /> : null}
          {incidents.data?.items.length === 0 ? <EmptyState title="No active incidents" description="Correlated activity will appear here when the detection pipeline finds a priority case." /> : null}
          {incidents.data?.items.length ? (
            <div className="queue-list">
              {incidents.data.items.map((incident) => (
                <Link className="queue-item" href={`/incidents/${incident.id}`} key={incident.id}>
                  <span className={`severity-dot severity-${incident.severity}`} />
                  <span className="queue-copy"><strong>{incident.title}</strong><small>{incident.primary_username ?? incident.primary_source_ip ?? "Unknown identity"}</small></span>
                  <span className="risk-score">{incident.risk_score}</span>
                </Link>
              ))}
            </div>
          ) : null}
        </article>

        <article className="panel activity-panel">
          <div className="panel-heading">
            <div><p className="eyebrow">Pipeline</p><h2>Detection flow</h2></div>
            <TrendingUp size={20} />
          </div>
          <ol className="pipeline-list">
            <li><span>01</span><div><strong>Telemetry intake</strong><p>Service-key protected</p></div><i className="ok-dot" /></li>
            <li><span>02</span><div><strong>Rules + anomaly model</strong><p>Inline evaluation</p></div><i className="ok-dot" /></li>
            <li><span>03</span><div><strong>Incident correlation</strong><p>Identity-aware grouping</p></div><i className="ok-dot" /></li>
            <li><span>04</span><div><strong>AI investigation</strong><p>{summaryData?.investigations_active ? "Active analysis" : "Available on demand"}</p></div><i className={summaryData?.investigations_active ? "ok-dot" : "idle-dot"} /></li>
          </ol>
        </article>

        <article className="panel span-two coverage-panel">
          <div><p className="eyebrow">Coverage map</p><h2>Evidence layers connected</h2></div>
          <div className="coverage-track">
            {["Events", "Rules", "ML", "Incidents", "MITRE", "AI"].map((item, index) => (
              <div key={item}><span>{String(index + 1).padStart(2, "0")}</span><strong>{item}</strong></div>
            ))}
          </div>
        </article>
      </section>
    </div>
  );
}
