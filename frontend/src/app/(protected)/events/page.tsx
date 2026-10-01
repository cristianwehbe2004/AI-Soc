"use client";

import Link from "next/link";
import { Activity, Search } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useEvents } from "@/lib/api/hooks";
import type { EventFilters } from "@/lib/api/resources";
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

export default function EventsPage() {
  const [filters, setFilters] = useState<EventFilters>({ limit, offset: 0 });
  const events = useEvents(filters);

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = new FormData(event.currentTarget);
    const next: EventFilters = {
      limit,
      offset: 0,
      event_type: String(values.get("event_type") || undefined),
      category: String(values.get("category") || undefined),
      severity: String(values.get("severity") || undefined),
      username: String(values.get("username") || undefined),
      source_ip: String(values.get("source_ip") || undefined),
    };
    setFilters(next);
  }

  return (
    <div className="page-stack">
      <PageHeading eyebrow="Telemetry" title="Security events" description="Explore normalized authentication, network, application, and cloud telemetry." action={<span className="status-pill neutral"><Activity size={13} /> {events.data?.total ?? "—"} records</span>} />

      <form className="filter-panel panel" onSubmit={applyFilters}>
        <div className="filter-heading"><div><p className="eyebrow">Signal search</p><h2>Filter telemetry</h2></div><button className="secondary-button" type="submit"><Search size={15} /> Apply filters</button></div>
        <div className="filter-grid">
          <label>Event type<input name="event_type" placeholder="login_failure" /></label>
          <label>Category<select name="category" defaultValue=""><option value="">All categories</option><option value="authentication">Authentication</option><option value="network">Network</option><option value="cloud">Cloud</option><option value="application">Application</option><option value="file_access">File access</option><option value="privilege_change">Privilege change</option><option value="process">Process</option><option value="api">API</option></select></label>
          <label>Severity<select name="severity" defaultValue=""><option value="">All severities</option><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option><option value="critical">Critical</option></select></label>
          <label>Username<input name="username" placeholder="analyst@example.com" /></label>
          <label>Source IP<input name="source_ip" placeholder="198.51.100.10" /></label>
        </div>
      </form>

      <section className="panel table-panel">
        {events.isLoading ? <LoadingState label="Loading event stream" /> : null}
        {events.isError ? <ErrorState error={queryError(events.error)} onRetry={() => void events.refetch()} /> : null}
        {events.data?.items.length === 0 ? <EmptyState title="No matching events" description="Try broadening the filters or wait for new telemetry to arrive." /> : null}
        {events.data?.items.length ? (
          <>
            <DataTable label="Security events">
              <thead><tr><th>Timestamp</th><th>Event</th><th>Source</th><th>Identity</th><th>Severity</th><th>Status</th></tr></thead>
              <tbody>
                {events.data.items.map((item) => (
                  <tr key={item.id}>
                    <td className="table-mono">{formatDate(item.timestamp)}</td>
                    <td><Link className="table-link table-primary" href={`/events/${encodeURIComponent(item.event_id)}`}>{item.event_type}</Link><span className="table-subline">{item.category}</span></td>
                    <td><span className="table-primary">{item.source}</span><span className="table-subline">{item.source_type}</span></td>
                    <td>{item.username ?? <span className="table-muted">Unattributed</span>}<span className="table-subline">{item.source_ip ?? "No source IP"}</span></td>
                    <td><span className={`severity-badge severity-${item.severity ?? "unknown"}`}>{item.severity ?? "unknown"}</span></td>
                    <td>{item.status ?? <span className="table-muted">—</span>}</td>
                  </tr>
                ))}
              </tbody>
            </DataTable>
            <PaginationControls total={events.data.total} limit={events.data.limit} offset={events.data.offset} onChange={(offset) => setFilters((current) => ({ ...current, offset }))} />
          </>
        ) : null}
      </section>
    </div>
  );
}
