"use client";

import Link from "next/link";
import { BrainCircuit, ExternalLink, LoaderCircle, Plus } from "lucide-react";
import { useEffect } from "react";
import { useAuth } from "@/components/providers/auth-provider";
import { useInvestigations, useRequestInvestigation } from "@/lib/api/hooks";
import { hasPermission } from "@/lib/auth/permissions";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/data-state";

export function IncidentInvestigationsPanel({ incidentId }: { incidentId: string }) {
  const { user } = useAuth();
  const investigations = useInvestigations(incidentId);
  const request = useRequestInvestigation(incidentId);
  const canRequest = Boolean(user && hasPermission(user.role_name, "investigations:create"));

  useEffect(() => {
    const hasActive = investigations.data?.items.some((item) => item.status === "queued" || item.status === "running");
    if (!hasActive) return;
    const timer = window.setInterval(() => void investigations.refetch(), 5000);
    return () => window.clearInterval(timer);
  }, [investigations]);

  return (
    <section className="panel incident-panel">
      <div className="panel-heading"><div><p className="eyebrow">AI analysis</p><h2>Investigations</h2></div><BrainCircuit size={19} /></div>
      {investigations.isLoading ? <LoadingState label="Loading investigations" /> : null}
      {investigations.isError ? <ErrorState error={investigations.error instanceof Error ? investigations.error : new Error("Investigation service unavailable.")} onRetry={() => void investigations.refetch()} /> : null}
      {investigations.data?.items.length === 0 ? <EmptyState title="No investigation requested" description="Request an evidence-bound analysis when this incident needs deeper review." action={canRequest ? <button className="secondary-button" type="button" onClick={() => request.mutate()} disabled={request.isPending}><Plus size={15} /> Request analysis</button> : null} /> : null}
      {investigations.data?.items.length ? <div className="investigation-list">{investigations.data.items.map((item) => <article className="investigation-item" key={item.id}><div><span className={`status-badge status-${item.status}`}>{item.status}</span><strong>{item.provider} · {item.model}</strong><small>{new Date(item.created_at).toLocaleString()}</small></div>{item.status === "queued" || item.status === "running" ? <LoaderCircle className="spin" size={17} /> : <Link className="timeline-link" href={`/investigations/${item.id}`}>Open <ExternalLink size={12} /></Link>}</article>)}</div> : null}
      {request.isError ? <p className="inline-error">{request.error instanceof Error ? request.error.message : "The investigation could not be queued."}</p> : null}
      {investigations.data?.items.length ? <button className="secondary-button full-button" type="button" onClick={() => request.mutate()} disabled={!canRequest || request.isPending}><Plus size={15} /> {canRequest ? "Request another analysis" : "Analyst access required"}</button> : null}
    </section>
  );
}