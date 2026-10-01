"use client";

import Link from "next/link";
import { Search, ShieldAlert } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useIncidents } from "@/lib/api/hooks";
import type { IncidentFilters } from "@/lib/api/resources";
import { DataTable } from "@/components/ui/data-table";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/data-state";
import { PageHeading } from "@/components/ui/page-heading";
import { PaginationControls } from "@/components/ui/pagination-controls";

const limit = 25;

function queryError(error: unknown) {
  return error instanceof Error ? error : new Error("The API returned an unknown error.");
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en-US", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export default function IncidentsPage() {
  const [filters, setFilters] = useState<IncidentFilters>({ limit, offset: 0 });
  const incidents = useIncidents(filters);

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = new FormData(event.currentTarget);
    setFilters({
      limit,
      offset: 0,
      status: String(values.get("status") || undefined),
      severity: String(values.get("severity") || undefined),
      username: String(values.get("username") || undefined),
      source_ip: String(values.get("source_ip") || undefined),
    });
  }

  return (
    <div className="page-stack">
      <PageHeading eyebrow="Correlation" title="Incidents" description="Prioritize correlated activity and inspect the evidence behind every risk score." action={<span className="status-pill neutral"><ShieldAlert size={13} /> {incidents.data?.total ?? "—"} cases</span>} />
      <form className="filter-panel panel" onSubmit={applyFilters}>
        <div className="filter-heading"><div><p className="eyebrow">Triage search</p><h2>Filter incidents</h2></div><button className="secondary-button" type="submit"><Search size={15} /> Apply filters</button></div>
        <div className="filter-grid incident-filter-grid">
          <label>Status<select name="status" defaultValue=""><option value="">All statuses</option><option value="open">Open</option><option value="investigating">Investigating</option><option value="contained">Contained</option><option value="resolved">Resolved</option></select></label>
          <label>Severity<select name="severity" defaultValue=""><option value="">All severities</option><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option><option value="critical">Critical</option></select></label>
          <label>Username<input name="username" placeholder="victim-admin" /></label>
          <label>Source IP<input name="source_ip" placeholder="198.51.100.60" /></label>
        </div>
      </form>
      <section className="panel table-panel">
        {incidents.isLoading ? <LoadingState label="Loading incident queue" /> : null}
        {incidents.isError ? <ErrorState error={queryError(incidents.error)} onRetry={() => void incidents.refetch()} /> : null}
        {incidents.data?.items.length === 0 ? <EmptyState title="No incidents match" description="Correlated incidents will appear here when detection rules and ML identify a priority case." /> : null}
        {incidents.data?.items.length ? (
          <>
            <DataTable label="Incidents">
              <thead><tr><th>Incident</th><th>Severity</th><th>Status</th><th>Risk</th><th>Identity</th><th>Last seen</th></tr></thead>
              <tbody>{incidents.data.items.map((item) => <tr key={item.id}><td><Link className="table-link table-primary" href={`/incidents/${item.id}`}>{item.title}</Link><span className="table-subline">{item.id}</span></td><td><span className={`severity-badge severity-${item.severity}`}>{item.severity}</span></td><td><span className={`status-badge status-${item.status}`}>{item.status}</span></td><td><span className="risk-score">{item.risk_score}</span></td><td>{item.primary_username ?? <span className="table-muted">Unattributed</span>}<span className="table-subline">{item.primary_source_ip ?? "No source IP"}</span></td><td className="table-mono">{formatDate(item.last_seen)}</td></tr>)}</tbody>
            </DataTable>
            <PaginationControls total={incidents.data.total} limit={incidents.data.limit} offset={incidents.data.offset} onChange={(offset) => setFilters((current) => ({ ...current, offset }))} />
          </>
        ) : null}
      </section>
    </div>
  );
}
