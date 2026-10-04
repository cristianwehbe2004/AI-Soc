"use client";

import Link from "next/link";
import { ArrowRight, BrainCircuit, ShieldAlert, Sparkles } from "lucide-react";
import { useIncidents } from "@/lib/api/hooks";
import { PageHeading } from "@/components/ui/page-heading";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/data-state";

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en-US", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export default function InvestigationsPage() {
  const incidents = useIncidents({ limit: 50 });

  return (
    <div className="page-stack">
      <PageHeading
        eyebrow="AI Analysis & Investigation Queue"
        title="Incident Investigations"
        description="Select an active incident below to trigger an automated AI analysis or review existing investigation narratives."
        action={<BrainCircuit size={22} />}
      />

      <section className="panel table-panel" style={{ padding: "24px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
          <div>
            <p className="eyebrow">Available Cases</p>
            <h2 style={{ fontSize: "18px", fontWeight: 700 }}>Select an Incident to Investigate</h2>
          </div>
          <Link className="secondary-button" href="/incidents">
            <ShieldAlert size={15} /> All Incidents ({incidents.data?.total ?? "—"})
          </Link>
        </div>

        {incidents.isLoading ? <LoadingState label="Loading cases for investigation..." /> : null}
        {incidents.isError ? (
          <ErrorState
            error={incidents.error instanceof Error ? incidents.error : new Error("Could not load incidents")}
            onRetry={() => void incidents.refetch()}
          />
        ) : null}

        {incidents.data?.items.length === 0 ? (
          <EmptyState
            title="No active incidents"
            description="There are currently no correlated incidents available for AI investigation."
            action={
              <Link className="primary-link" href="/incidents">
                Go to Incidents Queue <ArrowRight size={15} />
              </Link>
            }
          />
        ) : null}

        {incidents.data?.items.length ? (
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            {incidents.data.items.map((item) => (
              <div
                key={item.id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "16px",
                  borderRadius: "10px",
                  border: "1px solid var(--border-color, #e2e8f0)",
                  background: "#ffffff",
                  gap: "16px",
                }}
              >
                <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <Link
                      href={`/incidents/${item.id}`}
                      style={{ fontWeight: 600, fontSize: "16px", color: "var(--ink, #0f172a)", textDecoration: "none" }}
                    >
                      {item.title}
                    </Link>
                    <span className={`severity-badge severity-${item.severity}`}>{item.severity}</span>
                    <span className={`status-badge status-${item.status}`}>{item.status}</span>
                  </div>
                  <div style={{ fontSize: "13px", color: "#64748b" }}>
                    Target User: <strong>{item.primary_username ?? "Unattributed"}</strong> | Source IP: <strong>{item.primary_source_ip ?? "N/A"}</strong> | Last Seen: {formatDate(item.last_seen)}
                  </div>
                </div>

                <Link
                  className="primary-button"
                  href={`/incidents/${item.id}`}
                  style={{ textDecoration: "none", whiteSpace: "nowrap" }}
                >
                  <Sparkles size={16} /> Open & Investigate <ArrowRight size={15} />
                </Link>
              </div>
            ))}
          </div>
        ) : null}
      </section>
    </div>
  );
}
