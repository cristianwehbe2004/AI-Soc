import { ExternalLink, Fingerprint } from "lucide-react";
import type { getIncident } from "@/lib/api/resources";

type Incident = Awaited<ReturnType<typeof getIncident>>;

export function IncidentMitrePanel({ techniques }: { techniques: Incident["techniques"] }) {
  const uniqueTechniques = Array.from(new Map(techniques.map((technique) => [technique.external_id, technique])).values());
  return (
    <section className="panel incident-panel">
      <div className="panel-heading"><div><p className="eyebrow">ATT&CK context</p><h2>MITRE techniques</h2></div><Fingerprint size={19} /></div>
      {uniqueTechniques.length === 0 ? <div className="panel-empty">No MITRE techniques are mapped to the correlated rules.</div> : <div className="technique-list">{uniqueTechniques.map((technique) => <article className="technique-item" key={technique.external_id}><strong>{technique.name}</strong><span>{technique.external_id} · {technique.tactics.join(" / ")}</span><p>{technique.description}</p><a className="timeline-link" href={technique.source_url} target="_blank" rel="noreferrer">Open ATT&CK source <ExternalLink size={12} /></a></article>)}</div>}
    </section>
  );
}