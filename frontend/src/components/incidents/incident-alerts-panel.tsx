import { AlertTriangle } from "lucide-react";
import type { getIncident } from "@/lib/api/resources";

type Incident = Awaited<ReturnType<typeof getIncident>>;

export function IncidentAlertsPanel({ alerts }: { alerts: Incident["alerts"] }) {
  return (
    <section className="panel incident-panel">
      <div className="panel-heading"><div><p className="eyebrow">Detection evidence</p><h2>Correlated alerts</h2></div><span className="panel-count">{alerts.length} alerts</span></div>
      {alerts.length === 0 ? <div className="panel-empty">No alerts are attached to this incident.</div> : <div className="alert-list">{alerts.map((alert) => <article className="alert-item" key={alert.id}><div className="alert-item-top"><h3>{alert.title}</h3><span className={`severity-badge severity-${alert.severity}`}>{alert.severity}</span></div><p>{alert.description}</p><small><AlertTriangle size={12} /> {alert.rule_id} · {alert.status} · {Math.round(alert.confidence * 100)}% confidence</small></article>)}</div>}
    </section>
  );
}