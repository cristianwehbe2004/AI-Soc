"use client";

import Link from "next/link";
import { ArrowRight, Plus, RotateCcw, Search, ShieldAlert, Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, type FormEvent, useRef } from "react";
import { useIncidents } from "@/lib/api/hooks";
import type { IncidentFilters } from "@/lib/api/resources";
import { DataTable } from "@/components/ui/data-table";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/data-state";
import { PageHeading } from "@/components/ui/page-heading";
import { PaginationControls } from "@/components/ui/pagination-controls";
import { CreateIncidentModal } from "@/components/incidents/create-incident-modal";
import { useAuth } from "@/components/providers/auth-provider";
import { hasPermission } from "@/lib/auth/permissions";

const limit = 25;

function queryError(error: unknown) {
  return error instanceof Error ? error : new Error("The API returned an unknown error.");
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en-US", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export default function IncidentsPage() {
  const router = useRouter();
  const { user } = useAuth();
  const formRef = useRef<HTMLFormElement>(null);
  const [filters, setFilters] = useState<IncidentFilters>({ limit, offset: 0 });
  const [isModalOpen, setIsModalOpen] = useState(false);
  const incidents = useIncidents(filters);
  const canCreate = Boolean(user && hasPermission(user.role_name, "incidents:write"));

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = new FormData(event.currentTarget);
    setFilters({
      limit,
      offset: 0,
      status: String(values.get("status") || "") || undefined,
      severity: String(values.get("severity") || "") || undefined,
      username: String(values.get("username") || "") || undefined,
      source_ip: String(values.get("source_ip") || "") || undefined,
    });
  }

  function resetFilters() {
    formRef.current?.reset();
    setFilters({ limit, offset: 0 });
  }

  const hasActiveFilters = Boolean(
    filters.status || filters.severity || filters.username || filters.source_ip
  );

  return (
    <div className="page-stack">
      <PageHeading
        eyebrow="Correlation"
        title="Incidents"
        description="Prioritize correlated activity and inspect the evidence behind every risk score."
        action={
          <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
            <span className="status-pill neutral">
              <ShieldAlert size={13} /> {incidents.data?.total ?? "—"} cases
            </span>
            {canCreate && (
              <button
                className="primary-button"
                type="button"
                onClick={() => setIsModalOpen(true)}
              >
                <Plus size={16} /> New Incident
              </button>
            )}
          </div>
        }
      />

      <CreateIncidentModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
      />

      <form className="filter-panel panel" ref={formRef} onSubmit={applyFilters}>
        <div className="filter-heading">
          <div>
            <p className="eyebrow">Triage search</p>
            <h2>Filter incidents</h2>
          </div>
          <div style={{ display: "flex", gap: "8px" }}>
            {hasActiveFilters && (
              <button
                className="secondary-button"
                type="button"
                onClick={resetFilters}
              >
                <RotateCcw size={15} /> Reset filters
              </button>
            )}
            <button className="primary-button" type="submit">
              <Search size={15} /> Apply filters
            </button>
          </div>
        </div>
        <div className="filter-grid incident-filter-grid">
          <label>
            Status
            <select name="status" defaultValue="">
              <option value="">All statuses</option>
              <option value="open">Open</option>
              <option value="investigating">Investigating</option>
              <option value="contained">Contained</option>
              <option value="resolved">Resolved</option>
            </select>
          </label>
          <label>
            Severity
            <select name="severity" defaultValue="">
              <option value="">All severities</option>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
          </label>
          <label>
            Username
            <input name="username" placeholder="e.g. victim-admin" />
          </label>
          <label>
            Source IP
            <input name="source_ip" placeholder="e.g. 198.51.100.60" />
          </label>
        </div>
      </form>
      <section className="panel table-panel">
        {incidents.isLoading ? <LoadingState label="Loading incident queue" /> : null}
        {incidents.isError ? (
          <ErrorState
            error={queryError(incidents.error)}
            onRetry={() => void incidents.refetch()}
          />
        ) : null}
        {incidents.data?.items.length === 0 ? (
          <EmptyState
            title="No incidents match"
            description="Correlated incidents will appear here when detection rules and ML identify a priority case."
            action={
              <div style={{ display: "flex", gap: "8px" }}>
                {hasActiveFilters && (
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={resetFilters}
                  >
                    <RotateCcw size={15} /> Reset filters
                  </button>
                )}
                {canCreate && (
                  <button
                    className="primary-button"
                    type="button"
                    onClick={() => setIsModalOpen(true)}
                  >
                    <Sparkles size={15} /> Create a New Incident
                  </button>
                )}
              </div>
            }
          />
        ) : null}
        {incidents.data?.items.length ? (
          <>
            <DataTable label="Incidents">
              <thead>
                <tr>
                  <th>Incident</th>
                  <th>Severity</th>
                  <th>Status</th>
                  <th>Risk</th>
                  <th>Identity</th>
                  <th>Last seen</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {incidents.data.items.map((item) => (
                  <tr
                    key={item.id}
                    onClick={() => router.push(`/incidents/${item.id}`)}
                    style={{ cursor: "pointer" }}
                  >
                    <td>
                      <Link
                        className="table-link table-primary"
                        href={`/incidents/${item.id}`}
                        onClick={(e) => e.stopPropagation()}
                      >
                        {item.title}
                      </Link>
                      <span className="table-subline">{item.id}</span>
                    </td>
                    <td>
                      <span className={`severity-badge severity-${item.severity}`}>
                        {item.severity}
                      </span>
                    </td>
                    <td>
                      <span className={`status-badge status-${item.status}`}>
                        {item.status}
                      </span>
                    </td>
                    <td>
                      <span className="risk-score">{item.risk_score}</span>
                    </td>
                    <td>
                      {item.primary_username ?? (
                        <span className="table-muted">Unattributed</span>
                      )}
                      <span className="table-subline">
                        {item.primary_source_ip ?? "No source IP"}
                      </span>
                    </td>
                    <td className="table-mono">{formatDate(item.last_seen)}</td>
                    <td>
                      <Link
                        className="secondary-button"
                        style={{ padding: "4px 10px", fontSize: "12px" }}
                        href={`/incidents/${item.id}`}
                        onClick={(e) => e.stopPropagation()}
                      >
                        Open <ArrowRight size={13} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </DataTable>
            <PaginationControls
              total={incidents.data.total}
              limit={incidents.data.limit}
              offset={incidents.data.offset}
              onChange={(offset) => setFilters((current) => ({ ...current, offset }))}
            />
          </>
        ) : null}
      </section>
    </div>
  );
}
