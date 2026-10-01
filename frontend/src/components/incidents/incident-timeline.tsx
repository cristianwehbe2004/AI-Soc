import Link from "next/link";
import { ArrowUpRight, CalendarClock } from "lucide-react";
import type { getIncident } from "@/lib/api/resources";

type Incident = Awaited<ReturnType<typeof getIncident>>;

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en-US", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export function IncidentTimeline({ entries }: { entries: Incident["timeline"] }) {
  return (
    <section className="panel incident-panel">
      <div className="panel-heading"><div><p className="eyebrow">Evidence sequence</p><h2>Timeline</h2></div><span className="panel-count">{entries.length} entries</span></div>
      {entries.length === 0 ? <div className="panel-empty">No timeline entries were materialized for this incident.</div> : <ol className="timeline-list">{entries.map((entry, index) => <li className="timeline-item" data-type={entry.type} key={`${entry.timestamp}-${entry.type}-${index}`}><span className="timeline-marker" /><div className="timeline-copy"><div className="timeline-meta"><CalendarClock size={13} /> {formatDate(entry.timestamp)} <span>{entry.type}</span></div><h3>{entry.title}</h3><p>{entry.description}</p>{entry.event_id ? <Link className="timeline-link" href={`/events/${encodeURIComponent(entry.event_id)}`}>Open event <ArrowUpRight size={13} /></Link> : null}</div></li>)}</ol>}
    </section>
  );
}