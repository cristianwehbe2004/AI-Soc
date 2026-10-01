"use client";

import Link from "next/link";
import { ArrowLeft, ExternalLink } from "lucide-react";
import { useParams } from "next/navigation";
import { useEvent } from "@/lib/api/hooks";
import { ErrorState, LoadingState } from "@/components/ui/data-state";
import { PageHeading } from "@/components/ui/page-heading";

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en-US", { dateStyle: "full", timeStyle: "long" }).format(new Date(value));
}

function queryError(error: unknown) {
  return error instanceof Error ? error : new Error("The API returned an unknown error.");
}

export default function EventDetailPage() {
  const params = useParams<{ eventId: string }>();
  const eventId = decodeURIComponent(params.eventId);
  const event = useEvent(eventId);

  if (event.isLoading) return <LoadingState label="Loading event detail" />;
  if (event.isError || !event.data) return <ErrorState error={queryError(event.error)} onRetry={() => void event.refetch()} />;

  const item = event.data;
  return (
    <div className="page-stack">
      <Link className="back-link" href="/events"><ArrowLeft size={15} /> Back to events</Link>
      <PageHeading eyebrow="Event detail" title={item.event_type} description={item.source} action={<span className={`severity-badge severity-${item.severity ?? "unknown"}`}>{item.severity ?? "unknown"}</span>} />
      <div className="detail-grid">
        <section className="panel detail-panel detail-span-two"><div className="panel-heading"><div><p className="eyebrow">Observed at</p><h2>{formatDate(item.timestamp)}</h2></div><span className="status-pill neutral">{item.event_id}</span></div><div className="metadata-grid"><div><span>Category</span><strong>{item.category}</strong></div><div><span>Source type</span><strong>{item.source_type}</strong></div><div><span>Status</span><strong>{item.status ?? "—"}</strong></div><div><span>Action</span><strong>{item.action ?? "—"}</strong></div><div><span>Username</span><strong>{item.username ?? "Unattributed"}</strong></div><div><span>Source IP</span><strong>{item.source_ip ?? "—"}</strong></div><div><span>Hostname</span><strong>{item.hostname ?? "—"}</strong></div><div><span>Resource</span><strong>{item.resource ?? "—"}</strong></div></div></section>
        <section className="panel detail-panel"><div className="panel-heading"><div><p className="eyebrow">Payload</p><h2>Raw evidence</h2></div><ExternalLink size={18} /></div><pre className="raw-payload">{JSON.stringify(item.raw_payload, null, 2)}</pre></section>
        <section className="panel detail-panel"><div className="panel-heading"><div><p className="eyebrow">Transport</p><h2>Event metadata</h2></div></div><div className="metadata-list"><div><span>Destination IP</span><strong>{item.destination_ip ?? "—"}</strong></div><div><span>Destination port</span><strong>{item.destination_port ?? "—"}</strong></div><div><span>Bytes sent</span><strong>{item.bytes_sent ?? "—"}</strong></div><div><span>Bytes received</span><strong>{item.bytes_received ?? "—"}</strong></div><div><span>Device</span><strong>{item.device_id ?? "—"}</strong></div><div><span>Country</span><strong>{item.country ?? "—"}</strong></div></div></section>
      </div>
    </div>
  );
}